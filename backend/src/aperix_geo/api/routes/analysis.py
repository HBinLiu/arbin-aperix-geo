"""Analysis aggregates (read-only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.db.models import Subject, User
from aperix_geo.services import analysis as analysis_svc
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["analysis"])


def _sub(db: Session, user: User, subject_id: UUID) -> Subject:
    s = (
        db.execute(
            select(Subject)
            .options(
                joinedload(Subject.competitor_domains),
                joinedload(Subject.competitor_brands),
            )
            .where(Subject.id == subject_id, Subject.tenant_id == user.tenant_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found")
    return s


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
    s = _sub(db, current, subject_id)
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
) -> list[dict]:
    _sub(db, current, subject_id)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_topics_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
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
    s = _sub(db, current, subject_id)
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
) -> list[dict]:
    _sub(db, current, subject_id)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_prompts_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
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
    s = _sub(db, current, subject_id)
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


@router.get("/subjects/{subject_id}/daily-visibility")
def daily_visibility(
    subject_id: UUID,
    dt_from: Annotated[str, Query(alias="from")],
    dt_to: Annotated[str, Query(alias="to")],
    db: DbSession,
    current: CurrentUser,
    platform: Annotated[list[str] | None, Query()] = None,
    topic_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    s = _sub(db, current, subject_id)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_daily_visibility_series(
        db,
        subject=s,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
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
) -> list[dict]:
    _sub(db, current, subject_id)
    f = parse_iso_datetime(dt_from)
    t = parse_iso_datetime(dt_to)
    return analysis_svc.build_platform_performance(
        db,
        subject_id=subject_id,
        dt_from=f,
        dt_to=t,
        platforms=platform or None,
        topic_id=topic_id,
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
    s = _sub(db, current, subject_id)
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
    s = _sub(db, current, subject_id)
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
