"""Recover sampling jobs stuck in queued/running after worker or process restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.finalize import finalize_sampling_job_db


def count_pending_responses(db: Session, job_id: UUID) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(LLMResponse)
            .where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == LLMResponseStatus.pending,
            )
        ).scalar_one()
        or 0
    )


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
    rcli = redis.from_url(settings.redis_url)
    return bool(rcli.set(_resume_debounce_key(job_id), "1", nx=True, ex=settings.sampling_resume_debounce_seconds))


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

    pending = count_pending_responses(db, job.id)
    if pending == 0:
        finalize_sampling_job_db(db, job.id)
        return True

    if not force and not is_sampling_job_stale(job, now=now):
        return False

    if not try_schedule_sampling_resume(job.id):
        return False

    from aperix_geo.tasks.sampling import sampling_orchestrate_job

    sampling_orchestrate_job.delay(str(job.id))
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
