"""Retry failed LLMResponse rows within an existing sampling job."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError
from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_resume


def failed_response_ids(db: Session, job_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(LLMResponse.id).where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == LLMResponseStatus.failed,
            )
        ).scalars().all()
    )


def retry_failed_responses_for_job(db: Session, job_id: UUID) -> int:
    """Reset failed rows to pending and re-dispatch only those responses."""
    job = db.get(SamplingJob, job_id)
    if job is None:
        raise SamplingJobError("Sampling job not found")

    response_ids = failed_response_ids(db, job_id)
    if not response_ids:
        raise SamplingJobError("No failed responses to retry")

    db.execute(
        update(LLMResponse)
        .where(LLMResponse.id.in_(response_ids))
        .values(status=LLMResponseStatus.pending, error_text="")
    )
    job.status = SamplingJobStatus.running
    job.finished_at = None
    job.error_message = ""
    if job.started_at is None:
        job.started_at = datetime.now(UTC)

    db.commit()
    db.refresh(job)
    enqueue_sampling_resume(job.id, response_ids)
    return len(response_ids)
