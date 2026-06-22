"""Shared bootstrap for sampling orchestrate/continue Celery tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.cache import warm_sampling_job_context
from aperix_geo.services.sampling.workflow.queues import response_work_queues


def load_active_job_work(
    db: Session,
    job_id: UUID,
    *,
    ensure_running: bool,
) -> tuple[SamplingJob | None, list[str], list[str], list[str]]:
    """Load pending/llm_ready/crawl_ready queues; optionally promote queued jobs to running."""
    job = db.get(SamplingJob, job_id)
    if not job:
        return None, [], [], []

    if ensure_running:
        job.status = SamplingJobStatus.running
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        db.commit()
    elif job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
        return None, [], [], []
    elif job.status == SamplingJobStatus.queued:
        job.status = SamplingJobStatus.running
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        db.commit()

    queues = response_work_queues(db, job_id)
    pending = queues.pending_strs
    llm_ready = queues.llm_ready_strs
    crawl_ready = queues.crawl_ready_strs
    if queues.has_work:
        warm_sampling_job_context(db, job_id=job_id)
    return job, pending, llm_ready, crawl_ready
