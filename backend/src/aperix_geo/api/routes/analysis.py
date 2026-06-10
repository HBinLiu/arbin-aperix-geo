"""Analysis aggregates (read-only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["analysis"])


@router.get("/subjects/{subject_id}/overview")
def overview(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_overview(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/topics-performance")
def topics_performance(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> list[dict]:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_topics_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/rank")
def rank(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_rank(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/prompts-performance")
def prompts_performance(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> list[dict]:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_prompts_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/citations")
def citations(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_citations(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/visibility-analysis")
def visibility_analysis(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_visibility_analysis(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/platforms-performance")
def platforms_performance(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> list[dict]:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_platform_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/platform-matrix")
def platform_matrix(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_platform_matrix_analysis(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/citation-analysis")
def citation_analysis(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_citation_analysis(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/citation-domain-analysis")
def citation_domain_analysis(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    host: Annotated[str, Query(min_length=1, max_length=255)],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_citation_domain_analysis(
        db,
        subject=s,
        host=host,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/citation-rank")
def citation_rank(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_citation_brand_rank(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/sentiment-analysis")
def sentiment_analysis(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_sentiment_analysis(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/daily-sentiment")
def daily_sentiment(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_daily_sentiment_series(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/content-opportunities")
def content_opportunities(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_content_opportunities(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/prompt-detail")
def prompt_detail(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
    prompt_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_prompt_detail_responses(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )


@router.get("/subjects/{subject_id}/backlink-opportunities")
def backlink_opportunities(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_backlink_opportunities(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )


@router.get("/subjects/{subject_id}/diagnosis")
def diagnosis(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_diagnosis(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
    )
