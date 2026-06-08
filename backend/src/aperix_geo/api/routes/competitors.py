"""Competitors for a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Subject
from aperix_geo.schemas.catalog import CompetitorItem, CompetitorsOut, CompetitorsUpdate
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.subject.rules import validate_brand_competitors
from aperix_geo.utils.domains import ensure_brand

router = APIRouter(tags=["competitors"])


def _serialize_competitors(s: Subject) -> CompetitorsOut:
    return CompetitorsOut(
        competitors=[
            CompetitorItem(
                domain=(c.domain or "").strip(),
                website_url=(c.website_url or "").strip(),
                brand=ensure_brand(c.brand, domain=c.domain),
                summary=(c.summary or "").strip(),
            )
            for c in s.competitors
        ],
    )


@router.get("/subjects/{subject_id}/competitors", response_model=CompetitorsOut)
def get_competitors(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return _serialize_competitors(s)


@router.put("/subjects/{subject_id}/competitors", response_model=CompetitorsOut)
def put_competitors(
    subject_id: UUID,
    body: CompetitorsUpdate,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    for c in list(s.competitors):
        db.delete(c)
    db.flush()

    apply_competitors(s, competitors=body.competitors)
    try:
        validate_brand_competitors(s)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(s)
    return _serialize_competitors(s)
