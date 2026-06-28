"""Competitors for a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Competitor, Subject
from aperix_geo.schemas.catalog import (
    CompetitorItem,
    CompetitorsOut,
    ConfiguredCompetitorItem,
    PromoteBrandOut,
)
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.http import quota_exceeded_http_exception
from aperix_geo.services.brand.sync import sync_subject_brands_from_setup
from aperix_geo.services.catalog import clear_analysis_entities_cache
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.competitor.persist import (
    DuplicateCompetitorError,
    InvalidCompetitorError,
    CompetitorNotFoundError,
    add_competitor,
    remove_competitor_by_id,
    update_competitor_by_id,
)
from aperix_geo.services.competitor.promote import PromoteBrandError, promote_open_brand_to_competitor
from aperix_geo.services.competitor.reconcile import demote_competitor_signals, realign_competitor_signal_entity_ids
from aperix_geo.services.sampling.cache import clear_subject_sampling_cache
from aperix_geo.services.subject.rules import validate_brand_competitors
from aperix_geo.utils.net import ensure_brand

router = APIRouter(tags=["competitors"])


def _serialize_competitor(c: Competitor) -> ConfiguredCompetitorItem:
    return ConfiguredCompetitorItem(
        id=c.id,
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


def _finalize_competitor_mutation(db: DbSession, subject: Subject, subject_id: UUID) -> None:
    sync_subject_brands_from_setup(db, subject=subject)
    db.commit()
    db.refresh(subject)
    clear_analysis_entities_cache(subject_id)
    clear_subject_sampling_cache(subject_id)


def _enrich_competitor_item(item: CompetitorItem) -> CompetitorItem:
    raw = {
        "domain": item.domain,
        "website_url": item.website_url,
        "brand": item.brand,
        "aliases": list(item.aliases),
        "summary": item.summary,
        "cross_validate_score": item.cross_validate_score,
        "cross_validate_reason": item.cross_validate_reason,
    }
    enriched = enrich_confirmed_competitors([raw], session=None)
    if not enriched:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid competitor fields")
    row = enriched[0]
    return CompetitorItem(
        domain=row["domain"],
        website_url=row["website_url"],
        brand=row["brand"],
        aliases=list(row.get("aliases") or []),
        summary=str(row.get("summary") or ""),
        cross_validate_score=row.get("cross_validate_score"),
        cross_validate_reason=str(row.get("cross_validate_reason") or ""),
    )


@router.get("/subjects/{subject_id}/competitors", response_model=CompetitorsOut)
def get_competitors(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    s = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return _serialize_competitors(s)


@router.post(
    "/subjects/{subject_id}/competitors",
    response_model=ConfiguredCompetitorItem,
    status_code=status.HTTP_201_CREATED,
)
def post_competitor(
    subject_id: UUID,
    body: CompetitorItem,
    db: DbSession,
    current: CurrentUser,
) -> ConfiguredCompetitorItem:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    item = _enrich_competitor_item(body)
    try:
        competitor = add_competitor(db, subject, item=item)
        realign_competitor_signal_entity_ids(db, subject=subject)
        validate_brand_competitors(subject)
    except QuotaExceededError as exc:
        db.rollback()
        raise quota_exceeded_http_exception(exc) from exc
    except DuplicateCompetitorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidCompetitorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    _finalize_competitor_mutation(db, subject, subject_id)
    return _serialize_competitor(competitor)


@router.patch(
    "/subjects/{subject_id}/competitors/{competitor_id}",
    response_model=ConfiguredCompetitorItem,
)
def patch_competitor(
    subject_id: UUID,
    competitor_id: UUID,
    body: CompetitorItem,
    db: DbSession,
    current: CurrentUser,
) -> ConfiguredCompetitorItem:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    try:
        competitor = update_competitor_by_id(
            db,
            subject,
            competitor_id=competitor_id,
            item=body,
        )
        realign_competitor_signal_entity_ids(db, subject=subject)
        validate_brand_competitors(subject)
    except CompetitorNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateCompetitorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidCompetitorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    _finalize_competitor_mutation(db, subject, subject_id)
    return _serialize_competitor(competitor)


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
    except QuotaExceededError as exc:
        db.rollback()
        raise quota_exceeded_http_exception(exc) from exc
    except PromoteBrandError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _finalize_competitor_mutation(db, subject, subject_id)

    return PromoteBrandOut(
        competitor=_serialize_competitor(result.competitor),
        brand_id=result.brand_id,
        entity_label=result.entity_label,
        signals_migrated=result.signals_migrated,
        signals_dropped=result.signals_dropped,
    )


@router.delete("/subjects/{subject_id}/competitors/{competitor_id}", response_model=CompetitorsOut)
def delete_competitor(
    subject_id: UUID,
    competitor_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> CompetitorsOut:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    try:
        removed_id = remove_competitor_by_id(db, subject, competitor_id=competitor_id)
        demote_competitor_signals(db, subject_id=subject.id, competitor_id=removed_id)
        validate_brand_competitors(subject)
    except CompetitorNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    _finalize_competitor_mutation(db, subject, subject_id)
    return _serialize_competitors(subject)
