"""Dev debug route: trigger sampling without frontend UI (secret header + env flag)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from aperix_geo.api.deps import DbSession
from aperix_geo.db.models import SamplingJob
from aperix_geo.schemas.sampling import SamplingJobCreate, SamplingJobOut
from aperix_geo.services.sampling.debug import assert_sampling_debug_access
from aperix_geo.services.sampling.workflow import SamplingJobError, enqueue_subject_sampling
from aperix_geo.services.subject.loader import load_subject_with_competitors

router = APIRouter(tags=["sampling-debug"])


@router.post(
    "/dev/subjects/{subject_id}/sampling-jobs",
    response_model=SamplingJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
def debug_create_sampling_job(
    subject_id: UUID,
    db: DbSession,
    body: SamplingJobCreate = SamplingJobCreate(),
    x_aperix_sampling_debug: Annotated[str | None, Header()] = None,
) -> SamplingJob:
    assert_sampling_debug_access(x_aperix_sampling_debug)
    subject = load_subject_with_competitors(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    try:
        return enqueue_subject_sampling(
            db,
            subject=subject,
            prompt_ids=body.prompt_ids,
            platforms=body.platforms,
        )
    except SamplingJobError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
