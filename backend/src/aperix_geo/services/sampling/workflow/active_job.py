"""Shared bootstrap and dispatch entrypoints for sampling orchestrate/continue."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.cache import warm_sampling_job_context
from aperix_geo.services.sampling.workflow.fill import dispatch_phases
from aperix_geo.services.sampling.workflow.finalize import schedule_job_finalize
from aperix_geo.services.sampling.workflow.queues import response_work_queues


def _promote_job_to_running(db: Session, job: SamplingJob) -> None:
    job.status = SamplingJobStatus.running
    if job.started_at is None:
        job.started_at = datetime.now(UTC)
    db.commit()


def load_active_job_work(
    db: Session,
    job_id: UUID,
    *,
    ensure_running: bool,
) -> tuple[SamplingJob | None, bool]:
    """Load work queues; optionally promote queued jobs to running."""
    job = db.get(SamplingJob, job_id)
    if not job:
        return None, False

    if ensure_running:
        _promote_job_to_running(db, job)
    elif job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return None, False
    elif job.status == SamplingJobStatus.queued:
        _promote_job_to_running(db, job)

    queues = response_work_queues(db, job_id)
    if queues.has_work:
        warm_sampling_job_context(db, job_id=job_id)
    return job, queues.has_work


def run_active_job(job_id: str, *, ensure_running: bool) -> None:
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        _, has_work = load_active_job_work(db, jid, ensure_running=ensure_running)
    finally:
        db.close()

    if not has_work:
        schedule_job_finalize(jid)
        return
    dispatch_phases(job_id)
