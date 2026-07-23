"""LLM response parsing: mentions, citations, ABSA sentiment."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.parse.pipeline import run_parse_pipeline
from aperix_geo.services.sampling.parsed import ParsedSamplingResult

__all__ = ["parse_llm_output"]


def parse_llm_output(
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
) -> ParsedSamplingResult:
    return run_parse_pipeline(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        search_queries=search_queries,
        search_query_events=search_query_events,
        sampling_job_id=sampling_job_id,
        db=db,
        fetch_pages=fetch_pages,
    )
