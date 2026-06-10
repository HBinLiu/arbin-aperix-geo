"""Sampling jobs and synchronous smoke test."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    Prompt,
    SamplingJob,
    SamplingJobStatus,
)
from aperix_geo.schemas.sampling import (
    SamplingJobCreate,
    SamplingJobOut,
    SamplingPlatformOut,
    SampleSyncRequest,
)
from aperix_geo.services.pipeline import build_pipeline_status
from aperix_geo.services.sampling.workflow import (
    SamplingJobError,
    chat_prompt_on_platform,
    enqueue_subject_sampling,
    parse_chat_result,
    persist_successful_response,
    resolve_platforms_for_sampling,
)
from aperix_geo.services.sampling.llm import (
    SamplingLLMError,
    list_sampling_platforms,
    resolve_sampling_platform,
)

router = APIRouter(tags=["sampling"])


@router.get("/sampling-platforms", response_model=list[SamplingPlatformOut])
def get_sampling_platforms(current: CurrentUser) -> list[dict[str, str]]:
    _ = current
    return list_sampling_platforms()


@router.get("/subjects/{subject_id}/pipeline-status")
def pipeline_status(subject_id: UUID, db: DbSession, current: CurrentUser) -> dict:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    return build_pipeline_status(db, subject_id=subject_id)


@router.post(
    "/subjects/{subject_id}/sampling-jobs",
    response_model=SamplingJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_sampling_job(
    subject_id: UUID,
    body: SamplingJobCreate,
    db: DbSession,
    current: CurrentUser,
) -> SamplingJob:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    try:
        return enqueue_subject_sampling(
            db,
            subject=subject,
            tenant_id=current.tenant_id,
            prompt_ids=body.prompt_ids,
            platforms=body.platforms,
        )
    except SamplingJobError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/sampling-jobs/{job_id}", response_model=SamplingJobOut)
def get_sampling_job(job_id: UUID, db: DbSession, current: CurrentUser) -> SamplingJob:
    job = db.get(SamplingJob, job_id)
    if not job or job.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/sampling-jobs/{job_id}/responses")
def list_job_responses(
    job_id: UUID,
    db: DbSession,
    current: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    job = db.get(SamplingJob, job_id)
    if not job or job.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = list(
        db.execute(
            select(LLMResponse)
            .where(LLMResponse.sampling_job_id == job_id)
            .order_by(LLMResponse.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "prompt_id": str(r.prompt_id),
                "platform": r.platform,
                "status": r.status.value,
                "error_text": r.error_text,
                "latency_ms": r.latency_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@router.post("/subjects/{subject_id}/sample-sync")
def sample_sync(
    subject_id: UUID,
    body: SampleSyncRequest,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    """Call LLM once for a prompt. When persist=True, writes raw_text + parsed."""
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    prompt = db.get(Prompt, body.prompt_id)
    if not prompt or prompt.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Prompt not found")

    try:
        platforms = resolve_platforms_for_sampling(
            subject,
            [body.platform] if body.platform else None,
        )
    except SamplingJobError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    platform = platforms[0]
    try:
        resolve_sampling_platform(platform)
    except SamplingLLMError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        result = chat_prompt_on_platform(platform, prompt.text)
    except SamplingLLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    result_payload: dict = {
        "platform": platform,
        "raw_text": result.text,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "source_urls": list(result.source_urls),
        "web_search_mode": result.web_search_mode,
        "persisted": False,
    }
    if not body.persist:
        return result_payload

    parsed = parse_chat_result(result, subject=subject)
    job = SamplingJob(
        tenant_id=current.tenant_id,
        subject_id=subject_id,
        status=SamplingJobStatus.succeed,
        total_items=1,
        completed_items=1,
        failed_items=0,
    )
    db.add(job)
    db.flush()
    row = LLMResponse(
        sampling_job_id=job.id,
        prompt_id=prompt.id,
        platform=platform,
        status=LLMResponseStatus.pending,
    )
    db.add(row)
    db.flush()
    persist_successful_response(db, row=row, result=result, parsed=parsed)
    db.commit()
    db.refresh(job)
    result_payload["persisted"] = True
    result_payload["job_id"] = str(job.id)
    result_payload["response_id"] = str(row.id)
    result_payload["parsed"] = parsed
    return result_payload
