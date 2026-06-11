"""Pipeline stage derivation from sampling jobs and parsed responses."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJobStatus
from aperix_geo.services.sampling.workflow.recovery import reconcile_active_sampling_job
from aperix_geo.services.sampling.workflow.schedule import get_latest_sampling_job


def build_pipeline_status(db: Session, *, subject_id: UUID) -> dict[str, Any]:
    job = get_latest_sampling_job(db, subject_id)

    if job:
        reconcile_active_sampling_job(db, job)
        db.refresh(job)

    if not job:
        return {
            "stage": "verify",
            "latest_job": None,
            "response_count": 0,
            "parsed_count": 0,
        }

    stats = db.execute(
        select(
            func.count(LLMResponse.id),
            func.count(LLMResponse.parsed),
        ).where(
            LLMResponse.sampling_job_id == job.id,
            LLMResponse.status == LLMResponseStatus.success,
        )
    ).one()
    response_count = int(stats[0] or 0)
    parsed_count = int(stats[1] or 0)

    if job.status in (SamplingJobStatus.queued, SamplingJobStatus.running):
        stage = "dispatch"
    elif job.status in (SamplingJobStatus.succeed, SamplingJobStatus.partial, SamplingJobStatus.failed):
        if response_count > 0 and parsed_count < response_count:
            stage = "clean"
        elif parsed_count > 0:
            stage = "analyze"
        elif job.status == SamplingJobStatus.failed:
            stage = "dispatch"
        else:
            stage = "clean"
    else:
        stage = "dispatch"

    return {
        "stage": stage,
        "latest_job": {
            "id": str(job.id),
            "status": job.status.value,
            "total_items": job.total_items,
            "completed_items": job.completed_items,
            "failed_items": job.failed_items,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        },
        "response_count": response_count,
        "parsed_count": parsed_count,
    }
