"""LLM response parsing: mentions, citations, ABSA sentiment."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.parse.analysis import enrich_parse_context, run_parse_analysis
from aperix_geo.services.sampling.parse.context import (
    ParseContext,
    build_parse_context,
    extract_parse_context,
)
from aperix_geo.services.sampling.parse.finalize import finalize_entity_signals, merge_parse_results
from aperix_geo.services.sampling.parse.pipeline import run_parse_pipeline
from aperix_geo.services.sampling.parse.types import (
    CitationParseParams,
    ParseEnrichment,
    ParseMergeResult,
)
from aperix_geo.services.sampling.parsed import ParsedSamplingResult

__all__ = [
    "CitationParseParams",
    "ParseContext",
    "ParseEnrichment",
    "ParseMergeResult",
    "build_parse_context",
    "enrich_parse_context",
    "extract_parse_context",
    "finalize_entity_signals",
    "merge_parse_results",
    "parse_llm_output",
    "run_parse_analysis",
    "run_parse_pipeline",
]


def parse_llm_output(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
    sampling_job_id: UUID | None = None,
    db: Session | None = None,
) -> ParsedSamplingResult:
    return run_parse_pipeline(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        sampling_job_id=sampling_job_id,
        db=db,
    )
