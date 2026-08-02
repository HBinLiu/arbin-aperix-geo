"""Parse pipeline orchestration: extract → enrich → merge."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.parse.analysis import enrich_parse_context
from aperix_geo.services.sampling.parse.context import extract_parse_context
from aperix_geo.services.sampling.parse.finalize import merge_parse_results
from aperix_geo.services.sampling.parsed import ParsedSamplingResult


def run_parse_pipeline(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
    search_queries: list[str] | None = None,
    search_query_events: list[dict] | None = None,
    sampling_job_id: UUID | None = None,
    db: Session | None = None,
    fetch_pages: bool = True,
    skip_absa: bool = False,
) -> ParsedSamplingResult:
    from aperix_geo.services.sampling.fanout import build_search_query_events

    ctx = extract_parse_context(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        sampling_job_id=sampling_job_id,
        db=db,
        skip_absa=skip_absa,
    )
    enrichment = enrich_parse_context(ctx, fetch_pages=fetch_pages)
    merged = merge_parse_results(ctx, enrichment=enrichment)
    queries = [str(q).strip() for q in (search_queries or []) if str(q).strip()]
    events = (
        [dict(event) for event in search_query_events if isinstance(event, dict)]
        if search_query_events
        else build_search_query_events(queries)
    )
    return ParsedSamplingResult(
        urls=ctx.urls,
        url_hosts=ctx.url_hosts,
        web_search_mode=ctx.web_search_mode,
        source_urls_from_api=list(ctx.source_urls or []),
        search_queries_from_api=queries,
        search_query_events=events,
        own_brand=ctx.own_brand,
        sentiment_source=merged.sentiment_source,
        citation_response_absa=merged.response_absa,
        citation_urls_own=list(enrichment.citation.citation_urls_own),
        citation_sources=list(enrichment.citation.citation_sources),
        entity_signals=merged.entity_signals,
        absa_live_call=enrichment.absa_live_call,
    )
