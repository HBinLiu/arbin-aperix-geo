"""Shared Celery phase runner for sampling_llm / sampling_crawl / sampling_parse."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.claim import (
    refresh_response_claim,
    release_response_claim,
    try_claim_response,
)
from aperix_geo.services.sampling.workflow.logging import log_sampling
from aperix_geo.services.sampling.workflow.persist_retry import retry_if_transient, run_persist_with_db_retry
from aperix_geo.services.sampling.workflow.types import SamplingTaskResult


@dataclass(frozen=True)
class SamplingPhaseSpec:
    phase: str
    expected_status: LLMResponseStatus
    prepare: Callable[[Session, LLMResponse, SamplingJob], SamplingTaskResult | None]
    work: Callable[..., Any]
    persist: Callable[[Session, UUID, Any], bool]
    fail: Callable[[Session, UUID, str], SamplingTaskResult]
    on_skipped: Callable[[], SamplingTaskResult]
    on_success: Callable[[], SamplingTaskResult]
    on_work_error: Callable[[Session, UUID, BaseException], SamplingTaskResult] | None = None


def _complete_dispatched_task(
    response_id: UUID,
    phase: str,
    *,
    job_id: UUID | None,
) -> None:
    """Release fill dispatch/inflight and schedule refill + finalize debounce."""
    from aperix_geo.services.sampling.workflow.fill import on_task_finished

    on_task_finished(response_id, phase, job_id=job_id)


def run_sampling_phase(task, response_id: str, spec: SamplingPhaseSpec) -> SamplingTaskResult:
    """Validate row state, run IO outside the row lock, then persist with DB retry."""
    rid = UUID(response_id)
    job_id: UUID | None = None

    prep_db = SessionLocal()
    try:
        row = prep_db.execute(
            select(LLMResponse).where(LLMResponse.id == rid).with_for_update()
        ).scalar_one_or_none()
        if not row:
            log_sampling(
                logging.WARNING,
                "采样阶段跳过：response 不存在",
                phase=spec.phase,
                response_id=rid,
            )
            _complete_dispatched_task(rid, spec.phase, job_id=None)
            return {"ok": False, "error": "missing response row"}

        job_id = row.sampling_job_id
        if row.status != spec.expected_status:
            prep_db.commit()
            log_sampling(
                logging.INFO,
                "采样阶段跳过：状态不匹配",
                phase=spec.phase,
                response_id=rid,
                job_id=job_id,
                expected_status=spec.expected_status.value,
                actual_status=row.status.value,
            )
            _complete_dispatched_task(rid, spec.phase, job_id=job_id)
            return {"ok": True, "skipped": True}

        job = prep_db.get(SamplingJob, job_id)
        if not job:
            from aperix_geo.services.sampling.workflow.execute import mark_response_failed

            mark_response_failed(prep_db, row=row, error_text="missing job")
            prep_db.commit()
            _complete_dispatched_task(rid, spec.phase, job_id=job_id)
            return {"ok": False, "error": "missing job"}

        early = spec.prepare(prep_db, row, job)
        if early is not None:
            prep_db.commit()
            _complete_dispatched_task(rid, spec.phase, job_id=job_id)
            return early

        prep_db.commit()
    finally:
        prep_db.close()

    if not try_claim_response(rid):
        log_sampling(
            logging.INFO,
            "采样阶段跳过：claim 丢失",
            phase=spec.phase,
            response_id=rid,
            job_id=job_id,
        )
        from aperix_geo.services.sampling.workflow.fill import on_task_claim_lost

        on_task_claim_lost(rid, spec.phase, job_id=job_id)
        return {"ok": True, "skipped": True, "reason": "claimed"}

    persist_db = SessionLocal()
    try:
        try:
            try:
                work_result = spec.work()
            except BaseException as exc:
                retry_if_transient(task, exc)
                if spec.on_work_error is not None:
                    result = spec.on_work_error(persist_db, rid, exc)
                    _complete_dispatched_task(rid, spec.phase, job_id=job_id)
                    return result
                raise

            refresh_response_claim(rid)

            result = run_persist_with_db_retry(
                task,
                persist_db,
                sampling_job_id=job_id,
                phase=spec.phase,
                persist=lambda: spec.persist(persist_db, rid, work_result),
                on_skipped=spec.on_skipped,
                on_success=spec.on_success,
                fail=lambda: spec.fail(persist_db, rid, "persist_failed"),
            )
            _complete_dispatched_task(rid, spec.phase, job_id=job_id)
            return result
        finally:
            release_response_claim(rid)
    finally:
        persist_db.close()
