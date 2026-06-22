"""Pipeline stage derivation from sampling jobs and parsed responses."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJobStatus
from aperix_geo.services.sampling.workflow.schedule import get_latest_sampling_job


def _response_counts_for_job(db: Session, job_id: UUID) -> dict[str, int]:
    pending = LLMResponseStatus.pending
    llm_ready = LLMResponseStatus.llm_ready
    crawl_ready = LLMResponseStatus.crawl_ready
    success = LLMResponseStatus.success
    rows = db.execute(
        select(
            func.count(LLMResponse.id).filter(LLMResponse.status == pending),
            func.count(LLMResponse.id).filter(LLMResponse.status == llm_ready),
            func.count(LLMResponse.id).filter(LLMResponse.status == crawl_ready),
            func.count(LLMResponse.id).filter(LLMResponse.status == success),
            func.count(LLMResponse.parsed).filter(LLMResponse.status == success),
        ).where(LLMResponse.sampling_job_id == job_id)
    ).one()
    return {
        "llm_pending_count": int(rows[0] or 0),
        "llm_ready_count": int(rows[1] or 0),
        "crawl_ready_count": int(rows[2] or 0),
        "response_count": int(rows[3] or 0),
        "parsed_count": int(rows[4] or 0),
    }


def _running_phase(
    *,
    llm_pending_count: int,
    llm_ready_count: int,
    crawl_ready_count: int,
) -> str | None:
    if llm_pending_count > 0:
        return "llm"
    if llm_ready_count > 0:
        return "crawl"
    if crawl_ready_count > 0:
        return "parse"
    return None


def build_pipeline_status(db: Session, *, subject_id: UUID) -> dict[str, Any]:
    job = get_latest_sampling_job(db, subject_id)

    if not job:
        return {
            "stage": "verify",
            "phase": None,
            "latest_job": None,
            "llm_pending_count": 0,
            "llm_ready_count": 0,
            "crawl_ready_count": 0,
            "response_count": 0,
            "parsed_count": 0,
        }

    counts = _response_counts_for_job(db, job.id)
    llm_pending_count = counts["llm_pending_count"]
    llm_ready_count = counts["llm_ready_count"]
    crawl_ready_count = counts["crawl_ready_count"]
    response_count = counts["response_count"]
    parsed_count = counts["parsed_count"]
    phase = _running_phase(
        llm_pending_count=llm_pending_count,
        llm_ready_count=llm_ready_count,
        crawl_ready_count=crawl_ready_count,
    )

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
        "phase": phase,
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
        "llm_pending_count": llm_pending_count,
        "llm_ready_count": llm_ready_count,
        "crawl_ready_count": crawl_ready_count,
        "response_count": response_count,
        "parsed_count": parsed_count,
    }
