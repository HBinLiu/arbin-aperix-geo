"""Competitors for a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.db.models import Subject, User
from aperix_geo.schemas.catalog import CompetitorDomainItem, CompetitorsOut, CompetitorsUpdate
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.subject.rules import validate_brand_competitors

router = APIRouter(tags=["competitors"])


def _sub(db: Session, user: User, subject_id: UUID) -> Subject:
    s = db.get(Subject, subject_id)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return s


def _domain_items_from_update(body: CompetitorsUpdate) -> list[CompetitorDomainItem]:
    if body.competitors:
        return body.competitors
    return [CompetitorDomainItem(domain=d, site_name="") for d in body.domains]


def _serialize_competitors(s: Subject) -> CompetitorsOut:
    competitors = [
        CompetitorDomainItem(
            domain=c.domain,
            website_url=(c.website_url or "").strip(),
            site_name=(c.site_name or "").strip(),
        )
        for c in s.competitor_domains
    ]
    return CompetitorsOut(
        competitors=competitors,
        domains=[c.domain for c in competitors],
        brand_names=[c.name for c in s.competitor_brands],
    )


@router.get("/subjects/{subject_id}/competitors", response_model=CompetitorsOut)
def get_competitors(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    s = _sub(db, current, subject_id)
    return _serialize_competitors(s)


@router.put("/subjects/{subject_id}/competitors", response_model=CompetitorsOut)
def put_competitors(
    subject_id: UUID,
    body: CompetitorsUpdate,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    s = _sub(db, current, subject_id)
    for c in list(s.competitor_domains):
        db.delete(c)
    for c in list(s.competitor_brands):
        db.delete(c)
    db.flush()

    apply_competitors(
        s,
        competitors=_domain_items_from_update(body),
        brand_names=body.brand_names,
    )
    try:
        validate_brand_competitors(s)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(s)
    return _serialize_competitors(s)
