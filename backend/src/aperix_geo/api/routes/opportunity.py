"""Opportunity aggregates (read-only)."""

from uuid import UUID

from fastapi import APIRouter

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.analysis_query import (
    BacklinkOpportunityDetailParams,
    BacklinkOpportunityParams,
    BacklinkOpportunityPromptsParams,
    BacklinkOpportunityUrlsParams,
    OpportunityWindowParams,
)
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["opportunity"])


def _parse_window(params: OpportunityWindowParams):
    dt_from = parse_iso_datetime(params.start_date)
    dt_to = parse_iso_datetime(params.end_date)
    return dt_from, dt_to


@router.post("/subjects/{subject_id}/opportunity/backlink")
def backlink_opportunity(
    subject_id: UUID,
    params: BacklinkOpportunityParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_backlink_opportunities(
        db,
        subject=s,
        platform=params.platform,
        topic_id=params.topic_id,
        search=params.search,
        sort_by=params.sort_by,
        order=params.order,
        dt_from=dt_from,
        dt_to=dt_to,
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
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_backlink_opportunity_detail(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=dt_from,
        dt_to=dt_to,
    )


@router.post("/subjects/{subject_id}/opportunity/backlink/detail/urls")
def backlink_opportunity_urls(
    subject_id: UUID,
    params: BacklinkOpportunityUrlsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_backlink_opportunity_urls_page(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=dt_from,
        dt_to=dt_to,
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
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_backlink_opportunity_prompts_page(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=dt_from,
        dt_to=dt_to,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )
