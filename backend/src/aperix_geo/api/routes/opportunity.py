"""Opportunity page aggregates (content & backlink)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.analysis_query import (
    BacklinkOpportunityDetailParams,
    BacklinkOpportunityParams,
    BacklinkOpportunityPromptsParams,
    BacklinkOpportunityUrlsParams,
    ContentOpportunityDetailParams,
    ContentOpportunityParams,
)
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["opportunity"])


@router.post("/subjects/{subject_id}/opportunity/content")
def content_opportunity(
    subject_id: UUID,
    params: ContentOpportunityParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_content_opportunities(
        db,
        subject=s,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        search=params.search,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


@router.post("/subjects/{subject_id}/opportunity/content/detail")
def content_opportunity_detail(
    subject_id: UUID,
    params: ContentOpportunityDetailParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    if params.prompt_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prompt_id required")
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_content_opportunity_detail(
        db,
        subject=s,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        platforms=params.platforms,
        dt_from=f,
        dt_to=t,
    )


@router.post("/subjects/{subject_id}/opportunity/backlink")
def backlink_opportunity(
    subject_id: UUID,
    params: BacklinkOpportunityParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_backlink_opportunities(
        db,
        subject=s,
        platform=params.platform,
        topic_id=params.topic_id,
        search=params.search,
        sort_by=params.sort_by,
        order=params.order,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/subjects/{subject_id}/opportunity/backlink/detail")
def backlink_opportunity_detail(
    subject_id: UUID,
    params: BacklinkOpportunityDetailParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_backlink_opportunity_detail(
        db,
        subject=s,
        host=params.host,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
    )


@router.post("/subjects/{subject_id}/opportunity/backlink/detail/urls")
def backlink_opportunity_urls(
    subject_id: UUID,
    params: BacklinkOpportunityUrlsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_backlink_opportunity_urls_page(
        db,
        subject=s,
        host=params.host,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


@router.post("/subjects/{subject_id}/opportunity/backlink/detail/prompts")
def backlink_opportunity_prompts(
    subject_id: UUID,
    params: BacklinkOpportunityPromptsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_backlink_opportunity_prompts_page(
        db,
        subject=s,
        host=params.host,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )
