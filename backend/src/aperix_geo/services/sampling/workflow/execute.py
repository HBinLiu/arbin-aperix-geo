"""Shared single-response sampling: LLM call, parse, persist."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.sampling.citation import replace_citations_for_response
from aperix_geo.services.sampling.llm import chat_for_platform
from aperix_geo.services.sampling.parser import parse_llm_output_typed
from aperix_geo.services.sampling.parsed import ParsedSamplingResult


def chat_prompt_on_platform(platform: str, prompt_text: str) -> SamplingChatResult:
    return chat_for_platform(platform, [{"role": "user", "content": prompt_text}])


def parse_chat_result(
    result: SamplingChatResult,
    *,
    subject: Subject,
    sampling_job_id: UUID | None = None,
) -> ParsedSamplingResult:
    return parse_llm_output_typed(
        result.text,
        subject=subject,
        source_urls=list(result.source_urls),
        web_search_mode=result.web_search_mode,
        sampling_job_id=sampling_job_id,
    )


def parse_stored_raw_text(
    raw_text: str,
    *,
    subject: Subject,
    parsed: dict | ParsedSamplingResult | None = None,
    web_search_mode: str | None = None,
    sampling_job_id: UUID | None = None,
) -> ParsedSamplingResult:
    """Re-parse an existing response; restores source_urls / web_search_mode when omitted."""
    prior = parsed.to_dict() if isinstance(parsed, ParsedSamplingResult) else (parsed or {})
    return parse_llm_output_typed(
        raw_text,
        subject=subject,
        source_urls=list(prior.get("source_urls_from_api") or []),
        web_search_mode=web_search_mode or str(prior.get("web_search_mode") or "none"),
        sampling_job_id=sampling_job_id,
    )


def persist_successful_response(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
    parsed: ParsedSamplingResult,
) -> None:
    row.raw_text = result.text
    row.parsed = parsed.to_dict()
    row.usage = result.usage
    row.latency_ms = result.latency_ms
    row.status = LLMResponseStatus.success
    row.error_text = ""
    replace_citations_for_response(
        db,
        response_id=row.id,
        prompt_id=row.prompt_id,
        parsed=parsed,
    )


def mark_response_failed(db: Session, *, row: LLMResponse, error_text: str) -> None:
    row.status = LLMResponseStatus.failed
    row.error_text = error_text[:4000]


def run_sample(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
    prompt_text: str,
) -> SamplingChatResult:
    """Call LLM, parse, and persist citations on one response row (caller commits)."""
    result = chat_prompt_on_platform(row.platform, prompt_text)
    parsed = parse_chat_result(result, subject=subject, sampling_job_id=row.sampling_job_id)
    persist_successful_response(db, row=row, result=result, parsed=parsed)
    return result


def reparse_response_row(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
) -> ParsedSamplingResult:
    """Re-run parse and refresh citations for an existing success row."""
    parsed = parse_stored_raw_text(
        row.raw_text or "",
        subject=subject,
        parsed=row.parsed,
        sampling_job_id=row.sampling_job_id,
    )
    row.parsed = parsed.to_dict()
    replace_citations_for_response(
        db,
        response_id=row.id,
        prompt_id=row.prompt_id,
        parsed=parsed,
    )
    return parsed
