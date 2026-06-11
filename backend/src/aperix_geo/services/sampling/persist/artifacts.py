"""Refresh derived artifacts (citations + signals) for one parsed response."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, Subject
from aperix_geo.services.sampling.citation import replace_citations_for_response
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist.brands import sync_brands_for_drafts
from aperix_geo.services.sampling.signals.persist import replace_llm_response_signals_for_response


def refresh_parsed_artifacts(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
    parsed: ParsedSamplingResult,
) -> None:
    """Replace citation rows and signal rows for one successful parse (no commit)."""
    replace_citations_for_response(
        db,
        response_id=row.id,
        prompt_id=row.prompt_id,
        parsed=parsed,
    )
    brands_by_entity_id = sync_brands_for_drafts(
        db,
        subject=subject,
        drafts=parsed.entity_signals,
        raw_text=row.raw_text or "",
        urls=list(parsed.urls or []),
    )
    replace_llm_response_signals_for_response(
        db,
        row=row,
        subject=subject,
        parsed=parsed,
        brands_by_entity_id=brands_by_entity_id,
    )
