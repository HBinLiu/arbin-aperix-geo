"""Enqueue Celery sampling orchestration without importing task modules."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.celery_app import celery_app

ORCHESTRATE_SAMPLING_JOB = "aperix_geo.tasks.sampling.sampling_orchestrate_job"
RESUME_PENDING_SAMPLING = "aperix_geo.tasks.sampling.sampling_resume_pending"


def enqueue_sampling_orchestration(job_id: UUID) -> None:
    celery_app.send_task(ORCHESTRATE_SAMPLING_JOB, args=[str(job_id)])


def enqueue_sampling_resume(job_id: UUID, response_ids: list[UUID]) -> None:
    """Re-dispatch only the given pending response rows (recovery path)."""
    if not response_ids:
        return
    celery_app.send_task(
        RESUME_PENDING_SAMPLING,
        args=[str(job_id), [str(response_id) for response_id in response_ids]],
    )
