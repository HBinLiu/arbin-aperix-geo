"""Replace per-response signal rows after parse."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, LLMResponse, LLMResponseSignal, Subject
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.signals.build import build_llm_response_signal_rows


def replace_llm_response_signals_for_response(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
    parsed: ParsedSamplingResult,
    brands_by_entity_id: dict[str, Brand] | None = None,
) -> None:
    db.execute(delete(LLMResponseSignal).where(LLMResponseSignal.response_id == row.id))
    db.flush()
    db.add_all(
        build_llm_response_signal_rows(
            response_id=row.id,
            subject_id=subject.id,
            prompt_id=row.prompt_id,
            platform=row.platform,
            created_at=row.created_at,
            entity_signals=parsed.entity_signals,
            brands_by_entity_id=brands_by_entity_id,
        )
    )
