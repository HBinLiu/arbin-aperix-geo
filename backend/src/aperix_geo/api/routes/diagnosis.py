"""Diagnosis center aggregates."""

from uuid import UUID

from fastapi import APIRouter

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.diagnosis_query import (
    DiagnosisContentDetailParams,
    DiagnosisContentParams,
    DiagnosisContentSummaryParams,
)
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["diagnosis"])


def _parse_window(params: DiagnosisContentSummaryParams):
    dt_from = parse_iso_datetime(params.start_date)
    dt_to = parse_iso_datetime(params.end_date)
    return dt_from, dt_to


@router.post("/subjects/{subject_id}/diagnosis")
def diagnosis_content(
    subject_id: UUID,
    params: DiagnosisContentParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_diagnosis_content(
        db,
        subject=s,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=params.platform,
        topic_id=params.topic_id,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


@router.post("/subjects/{subject_id}/diagnosis/summary")
def diagnosis_content_summary(
    subject_id: UUID,
    params: DiagnosisContentSummaryParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_diagnosis_content_summary(
        db,
        subject=s,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=params.platform,
        topic_id=params.topic_id,
    )


@router.post("/subjects/{subject_id}/diagnosis/detail")
def diagnosis_content_detail(
    subject_id: UUID,
    params: DiagnosisContentDetailParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_diagnosis_content_detail(
        db,
        subject=s,
        prompt_id=params.prompt_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=params.platform,
        topic_id=params.topic_id,
    )
