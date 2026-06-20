"""Competitors for a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Brand, Competitor, Subject
from aperix_geo.schemas.catalog import CompetitorItem, CompetitorsOut, CompetitorsUpdate, PromoteBrandOut
from aperix_geo.services.catalog import clear_analysis_entities_cache
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.competitor.promote import PromoteBrandError, promote_open_brand_to_competitor
from aperix_geo.services.subject.rules import validate_brand_competitors
from aperix_geo.utils.domains import ensure_brand

router = APIRouter(tags=["competitors"])


def _serialize_competitor(c: Competitor) -> CompetitorItem:
    return CompetitorItem(
        domain=(c.domain or "").strip(),
        website_url=(c.website_url or "").strip(),
        brand=ensure_brand(c.brand, domain=c.domain),
        aliases=list(c.aliases or []),
        summary=(c.summary or "").strip(),
    )


def _serialize_competitors(s: Subject) -> CompetitorsOut:
    return CompetitorsOut(
        competitors=[_serialize_competitor(c) for c in s.competitors],
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
    clear_analysis_entities_cache(subject_id)
    return _serialize_competitors(s)


@router.post(
    "/subjects/{subject_id}/brands/{brand_id}/promote",
    response_model=PromoteBrandOut,
)
def promote_brand_to_competitor(
    subject_id: UUID,
    brand_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> PromoteBrandOut:
    """Confirm an open-set brand as a configured competitor and migrate historical signals."""
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    try:
        result = promote_open_brand_to_competitor(db, subject=subject, brand_id=brand_id)
    except PromoteBrandError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    competitor = next(c for c in subject.competitors if c.id == result.competitor_id)
    db.commit()
    db.refresh(competitor)
    clear_analysis_entities_cache(subject_id)
    brand = db.get(Brand, result.brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="brand missing after promote")

    return PromoteBrandOut(
        competitor=_serialize_competitor(competitor),
        brand_id=brand.id,
        entity_label=result.entity_label,
        signals_migrated=result.signals_migrated,
        signals_dropped=result.signals_dropped,
    )
