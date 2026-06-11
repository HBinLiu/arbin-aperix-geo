"""LLM response parsing: mentions, citations, ABSA sentiment."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.parse.analysis import run_parse_analysis
from aperix_geo.services.sampling.parse.context import build_parse_context
from aperix_geo.services.sampling.parse.finalize import finalize_entity_signals
from aperix_geo.services.sampling.parsed import ParsedSamplingResult

__all__ = ["parse_llm_output"]


def parse_llm_output(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
    sampling_job_id: UUID | None = None,
) -> ParsedSamplingResult:
    ctx = build_parse_context(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        sampling_job_id=sampling_job_id,
    )
    citation, response_absa = run_parse_analysis(ctx)
    entity_signals, sentiment_source = finalize_entity_signals(
        ctx,
        citation=citation,
        response_absa=response_absa,
    )
    return ParsedSamplingResult(
        urls=ctx.urls,
        url_hosts=ctx.url_hosts,
        web_search_mode=ctx.web_search_mode,
        source_urls_from_api=list(ctx.source_urls or []),
        own_brand=ctx.own_brand,
        sentiment_source=sentiment_source,
        citation_response_absa=response_absa,
        citation_urls_own=list(citation.citation_urls_own),
        citation_sources=list(citation.citation_sources),
        entity_signals=entity_signals,
    )
