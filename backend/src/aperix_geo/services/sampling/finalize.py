"""Reconcile sampling job counters and terminal status from LLMResponse rows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus


def finalize_sampling_job_db(db: Session, job_id: UUID) -> SamplingJob | None:
    """Set job counters and terminal status from response rows. Returns the job."""
    job = db.get(SamplingJob, job_id)
    if not job:
        return None
    rows = db.execute(select(LLMResponse).where(LLMResponse.sampling_job_id == job_id)).scalars().all()
    ok = sum(1 for r in rows if r.status == LLMResponseStatus.success)
    fail = sum(1 for r in rows if r.status == LLMResponseStatus.failed)
    pending = sum(1 for r in rows if r.status == LLMResponseStatus.pending)
    job.completed_items = ok
    job.failed_items = fail
    if pending:
        job.status = SamplingJobStatus.partial
        job.error_message = f"{pending} response(s) still pending after workers finished"
    elif fail == 0:
        job.status = SamplingJobStatus.succeed
        job.error_message = ""
    elif ok == 0:
        job.status = SamplingJobStatus.failed
        job.error_message = "All sampling items failed"
    else:
        job.status = SamplingJobStatus.partial
        job.error_message = ""
    job.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
