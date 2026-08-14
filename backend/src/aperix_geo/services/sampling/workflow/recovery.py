"""Recover sampling jobs stuck in queued/running after worker or process restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.claim import response_claim_active
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db
from aperix_geo.services.sampling.workflow.queues import ResponseWorkQueues, response_work_queues
from aperix_geo.utils.datetime import ensure_utc
from sqlalchemy import select
from sqlalchemy.orm import Session


def sampling_job_activity_at(job: SamplingJob) -> datetime:
    """Last known activity timestamp used for stale detection."""
    return ensure_utc(job.updated_at or job.started_at or job.created_at)


def backlog_stale_seconds(*, settings: Settings | None = None) -> int:
    """Longer threshold while work remains (account-pool crawl may queue for hours)."""
    settings = settings or get_settings()
    crawl = int(float(settings.doubao_crawl_timeout_s))
    return min(
        6 * 3600,
        max(
            int(settings.sampling_stale_job_seconds) * 40,
            crawl * 60,
            3600,
        ),
    )


def job_has_active_response_claims(queues: ResponseWorkQueues) -> bool:
    """True when any in-flight pipeline response still holds a Redis worker claim."""
    for response_id in (*queues.pending, *queues.llm_ready, *queues.crawl_ready):
        if response_claim_active(response_id):
            return True
    return False


def is_sampling_job_stale(
    job: SamplingJob,
    *,
    now: datetime | None = None,
    stale_seconds: int | None = None,
    has_backlog: bool = False,
    has_active_claims: bool = False,
) -> bool:
    """True when an active job looks abandoned.

    - Mid-flight workers (active Redis claims) are never stale: claim TTL covers crashes.
    - Jobs with remaining work use a longer backlog window so single-account crawl
      queues are not wiped after ``SAMPLING_STALE_JOB_SECONDS`` (default 90s).
    """
    if job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return False
    if has_active_claims:
        return False
    settings = get_settings()
    if stale_seconds is not None:
        threshold = stale_seconds
    elif has_backlog:
        threshold = backlog_stale_seconds(settings=settings)
    else:
        threshold = int(settings.sampling_stale_job_seconds)
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

    has_claims = job_has_active_response_claims(queues)
    stale = is_sampling_job_stale(
        job,
        now=now,
        has_backlog=True,
        has_active_claims=has_claims,
    )
    if not force and not stale:
        return False

    from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_job_enqueue
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue

    if not try_schedule_sampling_job_enqueue(job.id, force=force):
        return False

    # Wipe locks only when abandoned (stale, no live claims). Force may re-fill without wipe.
    if stale and not has_claims:
        from aperix_geo.services.sampling.workflow.fill import (
            reset_all_dispatch_markers,
            reset_all_inflight_slots,
        )

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
