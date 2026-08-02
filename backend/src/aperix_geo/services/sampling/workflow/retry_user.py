"""User-triggered sampling retry / resume for a subject."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus, Subject
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.quota import lock_tenant_ai_quota, require_active_subscription, reserve_ai_usage
from aperix_geo.services.sampling.workflow.jobs import (
    SAMPLING_ERR_QUOTA_INSUFFICIENT,
    SAMPLING_ERR_SUBSCRIPTION_INACTIVE,
    SamplingJobError,
    enqueue_subject_sampling,
    raise_sampling_unavailable,
)
from aperix_geo.services.sampling.workflow.queues import response_work_queues
from aperix_geo.services.sampling.workflow.recovery import recover_active_sampling_job
from aperix_geo.services.sampling.workflow.schedule import get_latest_sampling_job, subject_has_active_sampling_job

_SUBSCRIPTION_EXPIRED_MSG = "订阅已过期，无法重试采样"
_AI_QUOTA_INSUFFICIENT_MSG = "AI 调用额度不足，无法重试采样"


def _reactivate_job(db: Session, job: SamplingJob) -> None:
    job.status = SamplingJobStatus.running
    job.error_message = ""
    if not job.started_at:
        job.started_at = datetime.now(UTC)
    # finished_at is NOT NULL; use started_at as placeholder while the job is active.
    job.finished_at = job.started_at
    db.commit()


def _require_retry_subscription(db: Session, tenant_id: UUID) -> None:
    try:
        require_active_subscription(db, tenant_id)
    except SubscriptionInactiveError as e:
        raise SamplingJobError(
            _SUBSCRIPTION_EXPIRED_MSG, code=SAMPLING_ERR_SUBSCRIPTION_INACTIVE
        ) from e


def _requeue_failed_responses(db: Session, job: SamplingJob) -> int:
    """Reset failed rows for retry. Returns how many need a fresh LLM reservation."""
    failed_rows = list(
        db.execute(
            select(LLMResponse).where(
                LLMResponse.sampling_job_id == job.id,
                LLMResponse.status == LLMResponseStatus.failed,
            )
        )
        .scalars()
        .all()
    )
    need_reserve = 0
    for row in failed_rows:
        row.error_text = ""
        if (row.raw_text or "").strip():
            # Already had LLM output; retry crawl/parse without re-billing sampling LLM.
            row.status = LLMResponseStatus.llm_ready
        else:
            row.status = LLMResponseStatus.pending
            row.quota_settled = False
            need_reserve += 1
    return need_reserve


def _reserve_for_retry(db: Session, *, job: SamplingJob, tenant_id: UUID, amount: int) -> None:
    if amount <= 0:
        return
    available = lock_tenant_ai_quota(db, tenant_id)
    if available <= 0:
        raise_sampling_unavailable(
            db,
            tenant_id,
            expired_msg=_SUBSCRIPTION_EXPIRED_MSG,
            quota_msg=_AI_QUOTA_INSUFFICIENT_MSG,
        )
    if available < amount:
        raise SamplingJobError(_AI_QUOTA_INSUFFICIENT_MSG, code=SAMPLING_ERR_QUOTA_INSUFFICIENT)
    try:
        reserve_ai_usage(db, tenant_id=tenant_id, amount=amount, job=job)
    except QuotaExceededError as e:
        raise SamplingJobError(
            _AI_QUOTA_INSUFFICIENT_MSG, code=SAMPLING_ERR_QUOTA_INSUFFICIENT
        ) from e


def retry_subject_sampling(db: Session, *, subject: Subject, tenant_id: UUID) -> SamplingJob:
    """Resume stuck work, retry failed responses, or enqueue a fresh job."""
    _require_retry_subscription(db, tenant_id)

    if subject_has_active_sampling_job(db, subject.id):
        job = get_latest_sampling_job(db, subject.id)
        if job is None:
            raise SamplingJobError("No sampling job found")
        recover_active_sampling_job(db, job, force=True)
        db.refresh(job)
        return job

    job = get_latest_sampling_job(db, subject.id)
    if job is None:
        return enqueue_subject_sampling(db, subject=subject, tenant_id=tenant_id)

    queues = response_work_queues(db, job.id)
    if queues.has_work:
        _resume_active_job(db, job)
        return job

    failed_exists = (
        db.execute(
            select(LLMResponse.id)
            .where(
                LLMResponse.sampling_job_id == job.id,
                LLMResponse.status == LLMResponseStatus.failed,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if failed_exists:
        need_reserve = _requeue_failed_responses(db, job)
        _reserve_for_retry(db, job=job, tenant_id=tenant_id, amount=need_reserve)
        _resume_active_job(db, job)
        return job

    return enqueue_subject_sampling(db, subject=subject, tenant_id=tenant_id)


def _resume_active_job(db: Session, job: SamplingJob) -> None:
    _reactivate_job(db, job)
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue

    enqueue_sampling_continue(job.id)
    db.refresh(job)
