"""Sampling job status and pipeline API (read-only for product UI)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import SamplingJob
from aperix_geo.schemas.sampling import SamplingJobOut, SamplingPlatformOut
from aperix_geo.services.sampling.workflow.status import build_pipeline_status
from aperix_geo.services.sampling.llm import list_sampling_platforms

router = APIRouter(tags=["sampling"])


@router.get("/sampling/platforms", response_model=list[SamplingPlatformOut])
def get_sampling_platforms(current: CurrentUser) -> list[dict[str, str]]:
    _ = current
    return list_sampling_platforms()


@router.get("/subjects/{subject_id}/pipeline-status")
def pipeline_status(subject_id: UUID, db: DbSession, current: CurrentUser) -> dict:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    return build_pipeline_status(db, subject_id=subject_id)


@router.get("/sampling-jobs/{job_id}", response_model=SamplingJobOut)
def get_sampling_job(job_id: UUID, db: DbSession, current: CurrentUser) -> SamplingJob:
    job = db.get(SamplingJob, job_id)
    if not job or job.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
