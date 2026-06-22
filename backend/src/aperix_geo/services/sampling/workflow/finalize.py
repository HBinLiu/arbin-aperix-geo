"""Reconcile sampling job counters and terminal status from LLMResponse rows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.schedule import commit_schedule_anchor_if_due


def _response_status_counts(db: Session, job_id: UUID) -> dict[LLMResponseStatus, int]:
    rows = db.execute(
        select(LLMResponse.status, func.count(LLMResponse.id))
        .where(LLMResponse.sampling_job_id == job_id)
        .group_by(LLMResponse.status)
    ).all()
    return {status: int(count) for status, count in rows}


def finalize_sampling_job_db(db: Session, job_id: UUID) -> SamplingJob | None:
    """Set job counters and terminal status from response rows. Returns the job."""
    job = db.execute(
        select(SamplingJob).where(SamplingJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if not job:
        return None

    counts = _response_status_counts(db, job_id)
    ok = counts.get(LLMResponseStatus.success, 0)
    fail = counts.get(LLMResponseStatus.failed, 0)
    pending = counts.get(LLMResponseStatus.pending, 0)
    llm_ready = counts.get(LLMResponseStatus.llm_ready, 0)
    crawl_ready = counts.get(LLMResponseStatus.crawl_ready, 0)
    job.completed_items = ok
    job.failed_items = fail

    if pending or llm_ready or crawl_ready:
        # Another chord may still be processing; keep job active.
        job.status = SamplingJobStatus.running
        job.error_message = ""
        job.finished_at = None
    elif fail == 0:
        job.status = SamplingJobStatus.succeed
        job.error_message = ""
        job.finished_at = datetime.now(UTC)
    elif ok == 0:
        job.status = SamplingJobStatus.failed
        job.error_message = "All sampling items failed"
        job.finished_at = datetime.now(UTC)
    else:
        job.status = SamplingJobStatus.partial
        job.error_message = ""
        job.finished_at = datetime.now(UTC)

    commit_schedule_anchor_if_due(db, job)
    db.commit()
    db.refresh(job)
    return job
