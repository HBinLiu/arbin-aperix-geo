"""Phase 2 — enrich: citation resolution and response ABSA."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aperix_geo.services.sampling.citation import CitationDocument, empty_citation_document
from aperix_geo.services.sampling.citation.resolve import (
    build_citation_document,
    fetch_citation_pages_for_urls,
    resolve_citation_sources,
)
from aperix_geo.services.sampling.citation.scope import cross_validated_other_brand_labels
from aperix_geo.services.sampling.filter import filter_open_brands_in_response_absa
from aperix_geo.services.sampling.parse.context import ParseContext
from aperix_geo.services.sampling.parse.types import CitationParseParams, ParseEnrichment
from aperix_geo.services.sampling.response_absa import analyze_response_absa
from aperix_geo.utils.url import filter_citation_urls


def _run_response_absa(ctx: ParseContext) -> dict[str, Any]:
    return analyze_response_absa(
        ctx.text,
        own_brand=ctx.own_brand,
        competitors=ctx.competitor_brand_names,
        excluded_keys=set(ctx.configured_brand_keys),
        cache_ttl_s=ctx.absa_cache_ttl_s,
    )


def _apply_open_brand_cross_validate(ctx: ParseContext, response_absa: dict[str, Any]) -> dict[str, Any]:
    if ctx.db is None:
        return response_absa
    return filter_open_brands_in_response_absa(
        ctx.db,
        subject=ctx.subject,
        response_absa=response_absa,
        raw_text=ctx.text,
        url_hosts=ctx.url_hosts,
    )


def _run_absa_pipeline(ctx: ParseContext) -> dict[str, Any]:
    response_absa = _run_response_absa(ctx)
    return _apply_open_brand_cross_validate(ctx, response_absa)


def _fetch_citation_pages(params: CitationParseParams) -> list:
    return fetch_citation_pages_for_urls(
        params.urls,
        crawl=params.crawl,
        snippet_chars=params.snippet_chars,
        sampling_job_id=params.sampling_job_id,
    )


def _build_citation_from_pages(
    params: CitationParseParams,
    pages: list,
    *,
    response_absa: dict[str, Any],
    absa_ran: bool,
) -> CitationDocument:
    cross_validated = cross_validated_other_brand_labels(response_absa) if absa_ran else []
    safe_urls = filter_citation_urls(list(params.urls))
    return build_citation_document(
        pages,
        safe_urls,
        root=params.root,
        own_names=params.own_names,
        own_brand=params.own_brand,
        competitors=params.competitors,
        entity_signals=params.entity_signals,
        cross_validated_other_brands=cross_validated,
        llm_enabled=params.llm_enabled,
        geo_cache_ttl_s=params.geo_cache_ttl_s,
        geo_batch_size=params.geo_batch_size,
    )


def enrich_parse_context(ctx: ParseContext) -> ParseEnrichment:
    params = ctx.citation
    need_citation = bool(ctx.urls)
    need_absa = ctx.absa_needed
    citation = empty_citation_document()
    response_absa: dict[str, Any] = {}

    if need_absa and need_citation:
        with ThreadPoolExecutor(max_workers=2) as pool:
            absa_future = pool.submit(_run_absa_pipeline, ctx)
            pages_future = pool.submit(_fetch_citation_pages, params)
            response_absa = absa_future.result()
            pages = pages_future.result()
        citation = _build_citation_from_pages(
            params,
            pages,
            response_absa=response_absa,
            absa_ran=True,
        )
    elif need_absa:
        response_absa = _run_absa_pipeline(ctx)
    elif need_citation:
        citation = resolve_citation_sources(
            params.urls,
            root=params.root,
            own_names=params.own_names,
            own_brand=params.own_brand,
            competitors=params.competitors,
            entity_signals=params.entity_signals,
            cross_validated_other_brands=[],
            crawl=params.crawl,
            snippet_chars=params.snippet_chars,
            llm_enabled=params.llm_enabled,
            geo_cache_ttl_s=params.geo_cache_ttl_s,
            geo_batch_size=params.geo_batch_size,
            sampling_job_id=params.sampling_job_id,
        )

    return ParseEnrichment(citation=citation, response_absa=response_absa)


def run_parse_analysis(ctx: ParseContext) -> tuple[CitationDocument, dict[str, Any]]:
    """Legacy API: returns (citation, response_absa) tuple."""
    enrichment = enrich_parse_context(ctx)
    return enrichment.citation, enrichment.response_absa
