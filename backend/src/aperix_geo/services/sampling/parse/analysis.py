"""Parallel citation resolution and response ABSA."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aperix_geo.services.sampling.citation import CitationDocument, empty_citation_document, resolve_citation_sources
from aperix_geo.services.sampling.parse.context import ParseContext
from aperix_geo.services.sampling.response_absa import analyze_response_absa


def run_response_absa(ctx: ParseContext) -> dict[str, Any]:
    return analyze_response_absa(
        ctx.text,
        own_brand=ctx.own_brand,
        competitors=ctx.competitor_brand_names,
        excluded_keys=set(ctx.configured_brand_keys),
        cache_ttl_s=ctx.absa_cache_ttl_s,
    )


def run_parse_analysis(ctx: ParseContext) -> tuple[CitationDocument, dict[str, Any]]:
    need_citation = bool(ctx.urls)
    need_absa = ctx.absa_needed
    citation = empty_citation_document()
    response_absa: dict[str, Any] = {}

    if need_citation and need_absa:
        with ThreadPoolExecutor(max_workers=2) as pool:
            citation_future = pool.submit(resolve_citation_sources, **ctx.citation_kwargs)
            absa_future = pool.submit(run_response_absa, ctx)
            citation = citation_future.result()
            response_absa = absa_future.result()
    elif need_citation:
        citation = resolve_citation_sources(**ctx.citation_kwargs)
    elif need_absa:
        response_absa = run_response_absa(ctx)

    return citation, response_absa
