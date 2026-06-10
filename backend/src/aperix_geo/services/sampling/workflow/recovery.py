"""Recover sampling jobs stuck in queued/running after worker or process restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db
from aperix_geo.utils.cache.redis_kv import redis_set_nx
from sqlalchemy import select
from sqlalchemy.orm import Session


def count_pending_responses(db: Session, job_id: UUID) -> int:
    return len(pending_response_ids(db, job_id))


def pending_response_ids(db: Session, job_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(LLMResponse.id).where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == LLMResponseStatus.pending,
            )
        ).scalars().all()
    )


def pending_response_id_strs(db: Session, job_id: UUID) -> list[str]:
    return [str(response_id) for response_id in pending_response_ids(db, job_id)]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def sampling_job_activity_at(job: SamplingJob) -> datetime:
    """Last known activity timestamp used for stale detection."""
    return _ensure_utc(job.updated_at or job.started_at or job.created_at)


def is_sampling_job_stale(job: SamplingJob, *, now: datetime | None = None, stale_seconds: int | None = None) -> bool:
    if job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return False
    settings = get_settings()
    threshold = stale_seconds if stale_seconds is not None else settings.sampling_stale_job_seconds
    now = now or datetime.now(UTC)
    return now - sampling_job_activity_at(job) >= timedelta(seconds=threshold)


def _resume_debounce_key(job_id: UUID) -> str:
    return f"aperix:sampling:resume:{job_id}"


def try_schedule_sampling_resume(job_id: UUID) -> bool:
    """Return True when a resume task was newly scheduled (Redis debounce)."""
    settings = get_settings()
    return redis_set_nx(
        _resume_debounce_key(job_id),
        ttl_s=settings.sampling_resume_debounce_seconds,
    )


def reconcile_active_sampling_job(
    db: Session,
    job: SamplingJob,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> bool:
    """Finalize or re-enqueue a stuck active job. Returns True if job state may have changed."""
    if job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return False

    pending_ids = pending_response_ids(db, job.id)
    if not pending_ids:
        finalize_sampling_job_db(db, job.id)
        return True

    if not force and not is_sampling_job_stale(job, now=now):
        return False

    if not try_schedule_sampling_resume(job.id):
        return False

    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_resume

    enqueue_sampling_resume(job.id, pending_ids)
    return True


def reconcile_stale_sampling_jobs(db: Session, *, force: bool = False) -> int:
    """Scan all active jobs and attempt recovery. Returns count of jobs touched."""
    jobs = list(
        db.execute(
            select(SamplingJob).where(SamplingJob.status.in_((SamplingJobStatus.queued, SamplingJobStatus.running)))
        ).scalars().all()
    )
    touched = 0
    for job in jobs:
        if reconcile_active_sampling_job(db, job, force=force):
            touched += 1
    return touched
