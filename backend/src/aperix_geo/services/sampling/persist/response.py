"""Persist parsed sampling results to DB stores."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist.artifacts import refresh_parsed_artifacts


def persist_successful_response(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
    parsed: ParsedSamplingResult,
    subject: Subject,
) -> None:
    """Write document JSONB and derived citation/signal rows (caller commits)."""
    row.raw_text = result.text
    row.parsed = parsed.to_dict()
    row.usage = result.usage
    row.latency_ms = result.latency_ms
    row.status = LLMResponseStatus.success
    row.error_text = ""
    refresh_parsed_artifacts(db, row=row, subject=subject, parsed=parsed)
