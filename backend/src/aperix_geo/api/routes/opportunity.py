"""Opportunity aggregates (read-only) + prompt fan-out promote/dismiss."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.analysis_query import (
    BacklinkOpportunityDetailParams,
    BacklinkOpportunityParams,
    BacklinkOpportunityPromptsParams,
    BacklinkOpportunityUrlsParams,
    OpportunityWindowParams,
    BrandParams,
    PromptFanoutOpportunityParams,
    PromptFanoutPromoteParams,
)
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.http import billing_http_exception
from aperix_geo.services.opportunity import (
    build_prompt_fanouts_page,
    dismiss_opportunity_prompt_fanout,
    promote_opportunity_prompt_fanout,
)
from aperix_geo.services.prompts.persist import PromptValidationError
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["opportunity"])


def _parse_window(params: OpportunityWindowParams):
    dt_from = parse_iso_datetime(params.start_date)
    dt_to = parse_iso_datetime(params.end_date)
    return dt_from, dt_to


def _prompt_fanout_mutation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (SubscriptionInactiveError, QuotaExceededError)):
        return billing_http_exception(exc, inactive_detail="订阅已过期，无法管理提示词")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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


@router.post("/subjects/{subject_id}/opportunity/brand")
def brand_opportunity(
    subject_id: UUID,
    params: BrandParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    return analysis_svc.build_brands(
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


@router.post("/subjects/{subject_id}/opportunity/prompt-fanouts")
def prompt_fanout_opportunity(
    subject_id: UUID,
    params: PromptFanoutOpportunityParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id)
    dt_from, dt_to = _parse_window(params)
    return build_prompt_fanouts_page(
        db,
        subject=s,
        dt_from=dt_from,
        dt_to=dt_to,
        topic_id=params.topic_id,
        search=params.search,
        status=params.status,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/subjects/{subject_id}/opportunity/prompt-fanouts/{fanout_id}/promote")
def prompt_fanout_opportunity_promote(
    subject_id: UUID,
    fanout_id: UUID,
    params: PromptFanoutPromoteParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    get_subject_for_user(db, current, subject_id)
    try:
        return promote_opportunity_prompt_fanout(
            db,
            subject_id=subject_id,
            fanout_id=fanout_id,
            enabled=params.enabled,
        )
    except (PromptValidationError, QuotaExceededError, SubscriptionInactiveError) as exc:
        raise _prompt_fanout_mutation_error(exc) from exc


@router.post("/subjects/{subject_id}/opportunity/prompt-fanouts/{fanout_id}/dismiss")
def prompt_fanout_opportunity_dismiss(
    subject_id: UUID,
    fanout_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    get_subject_for_user(db, current, subject_id)
    try:
        return dismiss_opportunity_prompt_fanout(
            db,
            subject_id=subject_id,
            fanout_id=fanout_id,
        )
    except PromptValidationError as exc:
        raise _prompt_fanout_mutation_error(exc) from exc
