"""Shared single-response sampling: LLM call, parse, persist."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.llm import chat_for_platform
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist import persist_successful_response, refresh_parsed_artifacts


def chat_prompt_on_platform(platform: str, prompt_text: str) -> SamplingChatResult:
    return chat_for_platform(platform, [{"role": "user", "content": prompt_text}])


def parse_chat_result(
    result: SamplingChatResult,
    *,
    subject: Subject,
    sampling_job_id: UUID | None = None,
    db: Session | None = None,
) -> ParsedSamplingResult:
    return parse_llm_output(
        result.text,
        subject=subject,
        source_urls=list(result.source_urls),
        web_search_mode=result.web_search_mode,
        sampling_job_id=sampling_job_id,
        db=db,
    )


def parse_stored_raw_text(
    raw_text: str,
    *,
    subject: Subject,
    parsed: dict | ParsedSamplingResult | None = None,
    web_search_mode: str | None = None,
    sampling_job_id: UUID | None = None,
    db: Session | None = None,
) -> ParsedSamplingResult:
    """Re-parse an existing response; restores source_urls / web_search_mode when omitted."""
    prior = parsed.to_dict() if isinstance(parsed, ParsedSamplingResult) else (parsed or {})
    return parse_llm_output(
        raw_text,
        subject=subject,
        source_urls=list(prior.get("source_urls_from_api") or []),
        web_search_mode=web_search_mode or str(prior.get("web_search_mode") or "none"),
        sampling_job_id=sampling_job_id,
        db=db,
    )


def mark_response_failed(db: Session, *, row: LLMResponse, error_text: str) -> None:
    row.status = LLMResponseStatus.failed
    row.error_text = error_text[:4000]


def mark_response_failed_if_pending(db: Session, *, response_id: UUID, error_text: str) -> bool:
    """Mark failed only when the row is still pending (caller commits)."""
    row = db.execute(
        select(LLMResponse).where(LLMResponse.id == response_id).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.status != LLMResponseStatus.pending:
        db.commit()
        return False
    mark_response_failed(db, row=row, error_text=error_text)
    db.commit()
    return True


def execute_sample_without_row_lock(
    *,
    platform: str,
    prompt_text: str,
    subject: Subject,
    sampling_job_id: UUID | None,
    db: Session,
) -> tuple[SamplingChatResult, ParsedSamplingResult]:
    """LLM + parse without holding a row lock (parse may write open-set brands)."""
    result = chat_prompt_on_platform(platform, prompt_text)
    parsed = parse_chat_result(
        result,
        subject=subject,
        sampling_job_id=sampling_job_id,
        db=db,
    )
    return result, parsed


def persist_sample_if_pending(
    db: Session,
    *,
    response_id: UUID,
    result: SamplingChatResult,
    parsed: ParsedSamplingResult,
    subject: Subject,
) -> bool:
    """Persist success only when the row is still pending (caller commits)."""
    row = db.execute(
        select(LLMResponse).where(LLMResponse.id == response_id).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.status != LLMResponseStatus.pending:
        db.commit()
        return False
    persist_successful_response(db, row=row, result=result, parsed=parsed, subject=subject)
    db.commit()
    return True


def run_sample(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
    prompt_text: str,
) -> SamplingChatResult:
    """Call LLM, parse, and persist citations on one response row (caller commits)."""
    result = chat_prompt_on_platform(row.platform, prompt_text)
    parsed = parse_chat_result(result, subject=subject, sampling_job_id=row.sampling_job_id, db=db)
    persist_successful_response(db, row=row, result=result, parsed=parsed, subject=subject)
    return result


def reparse_response_row(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
) -> ParsedSamplingResult:
    """Re-run parse and refresh citations for an existing success row."""
    locked = db.execute(
        select(LLMResponse).where(LLMResponse.id == row.id).with_for_update()
    ).scalar_one_or_none()
    if locked is None:
        raise ValueError("LLM response not found")
    parsed = parse_stored_raw_text(
        locked.raw_text or "",
        subject=subject,
        parsed=locked.parsed,
        sampling_job_id=locked.sampling_job_id,
        db=db,
    )
    locked.parsed = parsed.to_dict()
    refresh_parsed_artifacts(db, row=locked, subject=subject, parsed=parsed)
    return parsed
