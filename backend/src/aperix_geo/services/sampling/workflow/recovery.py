"""Recover sampling jobs stuck in queued/running after worker or process restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db
from aperix_geo.services.sampling.workflow.queues import response_work_queues
from aperix_geo.utils.datetime import ensure_utc
from sqlalchemy import select
from sqlalchemy.orm import Session


def sampling_job_activity_at(job: SamplingJob) -> datetime:
    """Last known activity timestamp used for stale detection."""
    return ensure_utc(job.updated_at or job.started_at or job.created_at)


def is_sampling_job_stale(job: SamplingJob, *, now: datetime | None = None, stale_seconds: int | None = None) -> bool:
    if job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return False
    settings = get_settings()
    threshold = stale_seconds if stale_seconds is not None else settings.sampling_stale_job_seconds
    now = now or datetime.now(UTC)
    return now - sampling_job_activity_at(job) >= timedelta(seconds=threshold)


def recover_active_sampling_job(
    db: Session,
    job: SamplingJob,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> bool:
    """Finalize or re-enqueue a stuck active job. Returns True if job state may have changed."""
    if job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return False

    queues = response_work_queues(db, job.id)
    if not queues.has_work:
        finalize_sampling_job_db(db, job.id)
        return True

    if not force and not is_sampling_job_stale(job, now=now):
        return False

    from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_job_enqueue
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue

    if not try_schedule_sampling_job_enqueue(job.id, force=force):
        return False

    if is_sampling_job_stale(job, now=now):
        from aperix_geo.services.sampling.workflow.fill import reset_all_dispatch_markers, reset_all_inflight_slots

        reset_all_inflight_slots(job.id)
        reset_all_dispatch_markers(job.id)
    enqueue_sampling_continue(job.id)
    return True


def recover_stale_sampling_jobs(db: Session, *, force: bool = False) -> int:
    """Scan all active jobs and attempt recovery. Returns count of jobs touched."""
    jobs = list(
        db.execute(
            select(SamplingJob).where(SamplingJob.status.in_((SamplingJobStatus.queued, SamplingJobStatus.running)))
        ).scalars().all()
    )
    touched = 0
    for job in jobs:
        if recover_active_sampling_job(db, job, force=force):
            touched += 1
    return touched
