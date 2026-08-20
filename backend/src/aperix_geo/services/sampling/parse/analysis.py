"""Phase 2 — enrich: citation resolution and response ABSA."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aperix_geo.services.sampling.citation import CitationDocument, empty_citation_document
from aperix_geo.services.sampling.citation.cache.page_meta import get_job_citation_page
from aperix_geo.services.sampling.citation.cache.url_meta import get_url_citation_page
from aperix_geo.services.sampling.citation.page import CitationPageMeta
from aperix_geo.services.sampling.citation.resolve import (
    build_citation_document,
    fetch_citation_pages_for_urls,
)
from aperix_geo.services.sampling.citation.scope import open_brand_labels_from_absa
from aperix_geo.services.sampling.parse.context import ParseContext
from aperix_geo.services.sampling.parse.types import CitationParseParams, ParseEnrichment
from aperix_geo.services.sampling.response_absa import analyze_response_absa
from aperix_geo.services.sampling.subject_context import subject_track_context
from aperix_geo.utils.net import (
    filter_citation_urls,
    host_from,
    registrable_from,
)


def _run_response_absa(ctx: ParseContext) -> tuple[dict[str, Any], bool]:
    return analyze_response_absa(
        ctx.text,
        own_brand=ctx.own_brand,
        competitors=ctx.closed_brand_names,
        own_brand_names=ctx.own_brand_names,
        competitor_brand_names=ctx.competitor_brand_names,
        excluded_keys=set(ctx.configured_brand_keys),
        cache_ttl_s=ctx.absa_cache_ttl_s,
        track_context=subject_track_context(ctx.subject),
    )


def _competitor_roots(params: CitationParseParams) -> set[str]:
    roots: set[str] = set()
    for entry in params.competitors:
        root = registrable_from(entry.domain) or host_from(entry.domain)
        if root:
            roots.add(root)
    return roots


def _fetch_citation_pages(params: CitationParseParams) -> list[CitationPageMeta]:
    return fetch_citation_pages_for_urls(
        params.urls,
        crawl=params.crawl,
        snippet_chars=params.snippet_chars,
        sampling_job_id=params.sampling_job_id,
        own_root=params.root,
        competitor_roots=_competitor_roots(params),
    )


def _page_domain(url: str) -> str:
    return registrable_from(url)


def _load_citation_pages_from_cache(params: CitationParseParams) -> list[CitationPageMeta]:
    """Load citation pages from job/global caches only (parse phase; no network)."""
    safe_urls = filter_citation_urls(list(params.urls))
    pages: list[CitationPageMeta] = []
    for url in safe_urls:
        cached = None
        if params.sampling_job_id is not None:
            cached = get_job_citation_page(params.sampling_job_id, url)
        if cached is None:
            cached = get_url_citation_page(url)
        if cached is not None:
            pages.append(CitationPageMeta.from_dict(cached))
        else:
            pages.append(CitationPageMeta(url=url, domain=_page_domain(url)))
    return pages


def crawl_citation_pages(params: CitationParseParams) -> list[CitationPageMeta]:
    """Fetch citation pages (crawl worker phase)."""
    if not params.urls:
        return []
    return _fetch_citation_pages(params)


def _build_citation_from_pages(
    params: CitationParseParams,
    pages: list[CitationPageMeta],
    *,
    response_absa: dict[str, Any],
    absa_ran: bool,
) -> CitationDocument:
    open_labels = open_brand_labels_from_absa(response_absa) if absa_ran else []
    safe_urls = filter_citation_urls(list(params.urls))
    return build_citation_document(
        pages,
        safe_urls,
        root=params.root,
        own_names=params.own_names,
        own_brand=params.own_brand,
        competitors=params.competitors,
        entity_signals=params.entity_signals,
        open_brand_labels=open_labels,
    )


def enrich_parse_context(ctx: ParseContext, *, fetch_pages: bool = True) -> ParseEnrichment:
    params = ctx.citation
    need_citation = bool(ctx.urls)
    need_absa = ctx.absa_needed
    citation = empty_citation_document()
    response_absa: dict[str, Any] = {}
    absa_live_call = False

    load_pages = _fetch_citation_pages if fetch_pages else _load_citation_pages_from_cache

    if need_absa and need_citation:
        with ThreadPoolExecutor(max_workers=2) as pool:
            absa_future = pool.submit(_run_response_absa, ctx)
            pages_future = pool.submit(load_pages, params)
            response_absa, absa_live_call = absa_future.result()
            pages = pages_future.result()
        citation = _build_citation_from_pages(
            params,
            pages,
            response_absa=response_absa,
            absa_ran=True,
        )
    elif need_absa:
        response_absa, absa_live_call = _run_response_absa(ctx)
    elif need_citation:
        pages = load_pages(params)
        citation = _build_citation_from_pages(
            params,
            pages,
            response_absa={},
            absa_ran=False,
        )

    return ParseEnrichment(citation=citation, response_absa=response_absa, absa_live_call=absa_live_call)
