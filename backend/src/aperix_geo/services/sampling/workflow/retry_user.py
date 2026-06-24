"""User-triggered sampling retry / resume for a subject."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus, Subject
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, enqueue_subject_sampling
from aperix_geo.services.sampling.workflow.queues import response_work_queues
from aperix_geo.services.sampling.workflow.recovery import recover_active_sampling_job
from aperix_geo.services.sampling.workflow.schedule import get_latest_sampling_job, subject_has_active_sampling_job


def _reactivate_job(db: Session, job: SamplingJob) -> None:
    job.status = SamplingJobStatus.running
    job.error_message = ""
    if not job.started_at:
        job.started_at = datetime.now(UTC)
    # finished_at is NOT NULL; use started_at as placeholder while the job is active.
    job.finished_at = job.started_at
    db.commit()


def retry_subject_sampling(db: Session, *, subject: Subject, tenant_id: UUID) -> SamplingJob:
    """Resume stuck work, retry failed responses, or enqueue a fresh job."""
    if subject_has_active_sampling_job(db, subject.id):
        job = get_latest_sampling_job(db, subject.id)
        if job is None:
            raise SamplingJobError("No sampling job found")
        recover_active_sampling_job(db, job, force=True)
        db.refresh(job)
        return job

    job = get_latest_sampling_job(db, subject.id)
    if job is None:
        return enqueue_subject_sampling(db, subject=subject, tenant_id=tenant_id)

    queues = response_work_queues(db, job.id)
    if queues.has_work:
        _resume_active_job(db, job)
        return job

    failed_exists = (
        db.execute(
            select(LLMResponse.id)
            .where(
                LLMResponse.sampling_job_id == job.id,
                LLMResponse.status == LLMResponseStatus.failed,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if failed_exists:
        db.execute(
            update(LLMResponse)
            .where(
                LLMResponse.sampling_job_id == job.id,
                LLMResponse.status == LLMResponseStatus.failed,
            )
            .values(status=LLMResponseStatus.pending, error_text="")
        )
        _resume_active_job(db, job)
        return job

    return enqueue_subject_sampling(db, subject=subject, tenant_id=tenant_id)


def _resume_active_job(db: Session, job: SamplingJob) -> None:
    _reactivate_job(db, job)
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue

    enqueue_sampling_continue(job.id)
    db.refresh(job)
