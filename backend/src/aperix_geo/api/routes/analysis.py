"""Analysis aggregates (read-only)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.analysis_query import (
    AnalysisPromptsParams,
    AnalysisRankWindowParams,
    AnalysisWindowParams,
    BacklinkOpportunityDetailParams,
    BacklinkOpportunityParams,
    BacklinkOpportunityPromptsParams,
    BacklinkOpportunityUrlsParams,
    CitationDomainAnalysisParams,
    CitationDomainPromptsParams,
    CitationDomainUrlsParams,
    CitationDomainsParams,
    CitationUrlsParams,
    PlatformAnalysisParams,
    AnalysisResponsesParams,
)
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["analysis"])


#概述页接口
@router.post("/subjects/{subject_id}/overview")
def overview(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_dashboard_overview(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-可见度接口
@router.post("/subjects/{subject_id}/analysis/visibility")
def visibility_analysis(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_visibility_analysis(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-主题表现接口
@router.post("/subjects/{subject_id}/analysis/topics")
def topics_performance(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> list[dict]:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_topics_performance(
        db,
        subject_id=subject_id,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-提示词表现接口
@router.post("/subjects/{subject_id}/analysis/prompts")
def prompts_performance(
    subject_id: UUID,
    params: AnalysisPromptsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_prompts_performance_page(
        db,
        subject_id=subject_id,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        search=params.search,
        dt_from=f,
        dt_to=t,
        sort_by=params.sort_by,
        order=params.order,
        page=params.page,
        page_size=params.page_size,
    )


#分析页-提示词详情接口
@router.post("/subjects/{subject_id}/analysis/prompt/detail")
def prompt_detail(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    if params.prompt_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt_id is required")
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_prompt_detail(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-AI平台接口
@router.post("/subjects/{subject_id}/analysis/platform")
def platform_analysis(
    subject_id: UUID,
    params: PlatformAnalysisParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_platform_analysis(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        matrix_row=params.matrix_row,
        dt_from=f,
        dt_to=t,
    )


#分析页-情感倾向接口
@router.post("/subjects/{subject_id}/analysis/sentiment")
def sentiment_analysis(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_sentiment_analysis(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-回复明细接口
@router.post("/subjects/{subject_id}/analysis/responses")
def analysis_responses(
    subject_id: UUID,
    params: AnalysisResponsesParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_analysis_responses(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        sentiment_label=params.sentiment_label,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


#分析页-引用率接口
@router.post("/subjects/{subject_id}/analysis/citation")
def citation_analysis_overview(
    subject_id: UUID,
    params: AnalysisWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_analysis(
        db,
        subject=s,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-引用域名接口
@router.post("/subjects/{subject_id}/analysis/citation/domains")
def citation_domains(
    subject_id: UUID,
    params: CitationDomainsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_domains_page(
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


#分析页-引用URL接口
@router.post("/subjects/{subject_id}/analysis/citation/urls")
def citation_urls(
    subject_id: UUID,
    params: CitationUrlsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_urls_page(
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


#分析页-引用域名接口
@router.post("/subjects/{subject_id}/analysis/citation/domain")
def citation_domain_analysis(
    subject_id: UUID,
    params: CitationDomainAnalysisParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_domain_analysis(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
    )


#分析页-引用域名URL接口
@router.post("/subjects/{subject_id}/analysis/citation/domain/urls")
def citation_domain_urls(
    subject_id: UUID,
    params: CitationDomainUrlsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_domain_urls_page(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


#分析页-引用域名提示词接口
@router.post("/subjects/{subject_id}/analysis/citation/domain/prompts")
def citation_domain_prompts(
    subject_id: UUID,
    params: CitationDomainPromptsParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_citation_domain_prompts_page(
        db,
        subject=s,
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        prompt_id=params.prompt_id,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )


#排行榜页面接口
@router.post("/subjects/{subject_id}/rank")
def rank(
    subject_id: UUID,
    params: AnalysisRankWindowParams,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(params.start_date)
    t = parse_iso_datetime(params.end_date)
    return analysis_svc.build_rank(
        db,
        subject=s,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
    )


# 潜在机会 · 反向链接
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
        domain=params.domain,
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
        domain=params.domain,
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
        domain=params.domain,
        platform=params.platform,
        topic_id=params.topic_id,
        dt_from=f,
        dt_to=t,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        order=params.order,
    )
