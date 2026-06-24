"""Persist parsed sampling results to DB stores."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.parse.context import extract_citation_urls
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist.artifacts import refresh_parsed_artifacts
from aperix_geo.utils.sanitize import sanitize_json_value, sanitize_text


def persist_llm_result(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
) -> None:
    """Store platform LLM output; parse/citation runs in a follow-up task."""
    row.raw_text = sanitize_text(result.text)
    row.parsed = sanitize_json_value(
        {
            "source_urls_from_api": list(result.source_urls),
            "web_search_mode": result.web_search_mode,
        }
    )
    row.usage = sanitize_json_value(result.usage or {})
    row.latency_ms = result.latency_ms
    urls, _ = extract_citation_urls(result.text, list(result.source_urls))
    if not urls:
        row.status = LLMResponseStatus.crawl_ready
    else:
        row.status = LLMResponseStatus.llm_ready
    row.error_text = ""


def persist_successful_response(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
    parsed: ParsedSamplingResult,
    subject: Subject,
) -> None:
    """Write document JSONB and derived citation/signal rows (caller commits)."""
    row.raw_text = sanitize_text(result.text)
    row.parsed = sanitize_json_value(parsed.to_dict())
    row.usage = sanitize_json_value(result.usage or {})
    row.latency_ms = result.latency_ms
    row.status = LLMResponseStatus.success
    row.error_text = ""
    refresh_parsed_artifacts(db, row=row, subject=subject, parsed=parsed)
