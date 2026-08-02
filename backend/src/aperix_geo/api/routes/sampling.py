"""Sampling job status and pipeline API (read-only for product UI)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from starlette.responses import StreamingResponse

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import SamplingJob
from aperix_geo.schemas.sampling import SamplingJobOut, SamplingPlatformOut
from aperix_geo.services.sampling.llm import list_sampling_platforms
from aperix_geo.services.billing.http import (
    CODE_QUOTA_EXCEEDED,
    subscription_inactive_http_exception,
)
from aperix_geo.services.sampling.workflow.jobs import (
    SAMPLING_ERR_QUOTA_INSUFFICIENT,
    SAMPLING_ERR_SUBSCRIPTION_INACTIVE,
    SamplingJobError,
)
from aperix_geo.services.sampling.workflow.pipeline import iter_pipeline_status_events
from aperix_geo.services.sampling.workflow.retry_user import retry_subject_sampling

router = APIRouter(tags=["sampling"])


@router.get("/sampling/platforms", response_model=list[SamplingPlatformOut])
def get_sampling_platforms(current: CurrentUser) -> list[dict[str, str]]:
    _ = current
    return list_sampling_platforms()


@router.get("/subjects/{subject_id}/pipeline/stream")
async def pipeline_status_stream(subject_id: UUID, db: DbSession, current: CurrentUser) -> StreamingResponse:
    get_subject_for_user(db, current, subject_id, with_competitors=True)

    async def event_source():
        async for chunk in iter_pipeline_status_events(
            subject_id=subject_id,
            tenant_id=current.tenant_id,
        ):
            yield chunk

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.post(
    "/subjects/{subject_id}/sampling-jobs/retry",
    response_model=SamplingJobOut,
)
def retry_sampling_job(subject_id: UUID, db: DbSession, current: CurrentUser) -> SamplingJob:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    try:
        return retry_subject_sampling(db, subject=subject, tenant_id=current.tenant_id)
    except SamplingJobError as exc:
        if exc.code == SAMPLING_ERR_SUBSCRIPTION_INACTIVE:
            raise subscription_inactive_http_exception(detail=str(exc)) from exc
        if exc.code == SAMPLING_ERR_QUOTA_INSUFFICIENT:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": CODE_QUOTA_EXCEEDED,
                    "dimension": "ai_requests",
                    "message": str(exc),
                },
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
