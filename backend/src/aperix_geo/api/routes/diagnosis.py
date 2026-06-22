"""Diagnosis center aggregates."""

from uuid import UUID

from fastapi import APIRouter

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.diagnosis_query import DiagnosisContentDetailParams, DiagnosisContentParams
from aperix_geo.services import analysis as analysis_svc

router = APIRouter(tags=["diagnosis"])


@router.post("/subjects/{subject_id}/diagnosis")
def diagnosis_content(
    subject_id: UUID,
    params: DiagnosisContentParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return analysis_svc.build_diagnosis_content(
        db,
        subject=s,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


@router.post("/subjects/{subject_id}/diagnosis/summary")
def diagnosis_content_summary(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return analysis_svc.build_diagnosis_content_summary(db, subject=s)


@router.post("/subjects/{subject_id}/diagnosis/detail")
def diagnosis_content_detail(
    subject_id: UUID,
    params: DiagnosisContentDetailParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return analysis_svc.build_diagnosis_content_detail(
        db,
        subject=s,
        prompt_id=params.prompt_id,
    )
