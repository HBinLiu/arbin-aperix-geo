"""Shared single-response sampling: LLM, crawl, parse, and persist."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.cache.llm_result import (
    load_cached_llm_result,
    save_cached_llm_result,
)
from aperix_geo.services.sampling.llm import chat_for_platform
from aperix_geo.services.sampling.llm_limits import llm_sampling_slot
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist import persist_llm_result, persist_successful_response, refresh_parsed_artifacts


def prepare_sample_chat_result(
    *,
    platform: str,
    prompt_text: str,
    response_id: UUID | None = None,
    cache: bool = False,
) -> tuple[SamplingChatResult, bool]:
    """Call platform LLM once. Returns ``(result, live_call)``; cache hits are not billed."""
    if cache and response_id is not None:
        cached = load_cached_llm_result(response_id)
        if cached is not None:
            return cached, False
    with llm_sampling_slot(platform):
        result = chat_for_platform(platform, [{"role": "user", "content": prompt_text}])
    if cache and response_id is not None:
        save_cached_llm_result(response_id, result)
    return result, True


def chat_result_from_row(row: LLMResponse) -> SamplingChatResult:
    """Rebuild SamplingChatResult from a row after the LLM phase."""
    prior = row.parsed if isinstance(row.parsed, dict) else {}
    return SamplingChatResult(
        text=row.raw_text or "",
        usage=dict(row.usage or {}),
        latency_ms=int(row.latency_ms or 0),
        source_urls=tuple(
            str(url)
            for url in (prior.get("source_urls_from_api") or [])
            if str(url).strip()
        ),
        web_search_mode=str(prior.get("web_search_mode") or "none"),
        search_queries=tuple(
            str(q) for q in (prior.get("search_queries_from_api") or []) if str(q).strip()
        ),
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
        search_queries=list(prior.get("search_queries_from_api") or []),
        search_query_events=list(prior.get("search_query_events") or []),
        sampling_job_id=sampling_job_id,
        db=db,
    )


def mark_response_failed(db: Session, *, row: LLMResponse, error_text: str) -> None:
    row.status = LLMResponseStatus.failed
    row.error_text = error_text[:4000]


def _with_locked_response(
    db: Session,
    *,
    response_id: UUID,
    expected_status: LLMResponseStatus,
    mutate: Callable[[LLMResponse], None],
) -> bool:
    row = db.execute(
        select(LLMResponse).where(LLMResponse.id == response_id).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.status != expected_status:
        db.commit()
        return False
    mutate(row)
    db.commit()
    return True


def mark_response_failed_if_pending(db: Session, *, response_id: UUID, error_text: str) -> bool:
    """Mark failed only when the row is still pending (caller commits)."""
    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.pending,
        mutate=lambda row: mark_response_failed(db, row=row, error_text=error_text),
    )


def mark_response_failed_if_llm_ready(db: Session, *, response_id: UUID, error_text: str) -> bool:
    """Mark failed only when the row is still awaiting crawl (caller commits)."""
    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.llm_ready,
        mutate=lambda row: mark_response_failed(db, row=row, error_text=error_text),
    )


def mark_response_failed_if_crawl_ready(db: Session, *, response_id: UUID, error_text: str) -> bool:
    """Mark failed only when the row is still awaiting parse (caller commits)."""
    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.crawl_ready,
        mutate=lambda row: mark_response_failed(db, row=row, error_text=error_text),
    )


def persist_llm_sample(
    db: Session,
    *,
    response_id: UUID,
    chat_result: SamplingChatResult,
    tenant_id: UUID,
    subject_id: UUID,
    live_call: bool,
) -> bool:
    """Persist LLM output when the row is still pending; bill on live provider calls."""

    def _mutate(row: LLMResponse) -> None:
        if live_call:
            from aperix_geo.services.billing.quota import consume_ai_usage

            consume_ai_usage(
                db,
                tenant_id=tenant_id,
                subject_id=subject_id,
                source="sampling",
                reference_id=response_id,
                platform=row.platform,
                usage=chat_result.usage,
            )
        persist_llm_result(db, row=row, result=chat_result)

    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.pending,
        mutate=_mutate,
    )


def persist_crawl_sample(db: Session, *, response_id: UUID) -> bool:
    """Mark citation crawl complete when the row is still llm_ready."""

    def _mark_crawl_ready(row: LLMResponse) -> None:
        row.status = LLMResponseStatus.crawl_ready
        row.error_text = ""

    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.llm_ready,
        mutate=_mark_crawl_ready,
    )


def persist_parsed_sample(
    db: Session,
    *,
    response_id: UUID,
    subject: Subject,
    chat_result: SamplingChatResult,
    parsed: ParsedSamplingResult,
    tenant_id: UUID,
    absa_live_call: bool,
) -> bool:
    """Persist citation/ABSA artifacts when the row awaits parse."""

    def _mutate(row: LLMResponse) -> None:
        if absa_live_call:
            from aperix_geo.services.billing.quota import consume_ai_usage

            consume_ai_usage(
                db,
                tenant_id=tenant_id,
                subject_id=subject.id,
                source="parse",
                reference_id=response_id,
                platform=row.platform,
                usage=chat_result.usage,
            )
        persist_successful_response(
            db,
            row=row,
            result=chat_result,
            parsed=parsed,
            subject=subject,
        )

    return _with_locked_response(
        db,
        response_id=response_id,
        expected_status=LLMResponseStatus.crawl_ready,
        mutate=_mutate,
    )


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
