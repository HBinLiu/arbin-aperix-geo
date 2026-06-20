"""Reconcile sampling job counters and terminal status from LLMResponse rows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus


def finalize_sampling_job_db(db: Session, job_id: UUID) -> SamplingJob | None:
    """Set job counters and terminal status from response rows. Returns the job."""
    job = db.execute(
        select(SamplingJob).where(SamplingJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if not job:
        return None
    rows = db.execute(select(LLMResponse).where(LLMResponse.sampling_job_id == job_id)).scalars().all()
    ok = sum(1 for r in rows if r.status == LLMResponseStatus.success)
    fail = sum(1 for r in rows if r.status == LLMResponseStatus.failed)
    pending = sum(1 for r in rows if r.status == LLMResponseStatus.pending)
    job.completed_items = ok
    job.failed_items = fail

    if pending:
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

    db.commit()
    db.refresh(job)
    return job
