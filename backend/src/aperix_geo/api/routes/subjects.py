"""Subject CRUD."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.routes import subject_setup
from aperix_geo.api.routes import knowledge as knowledge_routes
from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.schemas.catalog import SubjectOut, SubjectUpdate
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.http import quota_exceeded_http_exception
from aperix_geo.services.billing.quota import assert_platform_capacity, assert_subject_sampling_frequency
from aperix_geo.services.brand.sync import sync_subject_brands_from_setup
from aperix_geo.services.catalog import clear_analysis_entities_cache, get_analysis_entities
from aperix_geo.services.sampling.platforms import (
    SamplingPlatformError,
    validate_explicit_sampling_platforms,
)
from aperix_geo.services.subject.rules import validate_subject_fields
from aperix_geo.utils.net import ensure_brand

router = APIRouter(prefix="/subjects", tags=["subjects"])
router.include_router(subject_setup.router)
router.include_router(knowledge_routes.router)


def _validate_sampling_platforms(platforms: list[str]) -> list[str]:
    try:
        return validate_explicit_sampling_platforms(platforms)
    except SamplingPlatformError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("", response_model=list[SubjectOut])
def list_subjects(
    db: DbSession,
    current: CurrentUser,
) -> list[Subject]:
    return list(
        db.execute(
            select(Subject)
            .where(Subject.tenant_id == current.tenant_id)
            .order_by(Subject.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> Subject:
    return get_subject_for_user(db, current, subject_id)


@router.patch("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: UUID,
    body: SubjectUpdate,
    db: DbSession,
    current: CurrentUser,
) -> Subject:
    sub = get_subject_for_user(db, current, subject_id)
    brand_catalog_dirty = False
    if body.brand is not None:
        sub.brand = ensure_brand(
            body.brand,
            domain=sub.domain if sub.type == SubjectType.domain else None,
        )
        brand_catalog_dirty = True
    if body.aliases is not None:
        sub.aliases = list(body.aliases)
        brand_catalog_dirty = True
    if body.profile_summary is not None:
        sub.profile_summary = body.profile_summary
        brand_catalog_dirty = True
    if body.sampling_platforms is not None:
        platforms = _validate_sampling_platforms(body.sampling_platforms)
        try:
            assert_platform_capacity(db, current.tenant_id, len(platforms))
        except QuotaExceededError as exc:
            raise quota_exceeded_http_exception(exc) from exc
        sub.sampling_platforms = platforms
    if body.sampling_frequency is not None:
        try:
            sub.sampling_frequency = assert_subject_sampling_frequency(
                db,
                current.tenant_id,
                body.sampling_frequency,
            )
        except QuotaExceededError as exc:
            raise quota_exceeded_http_exception(exc) from exc
    if brand_catalog_dirty:
        sync_subject_brands_from_setup(db, subject=sub)
    validate_subject_fields(sub)
    db.commit()
    db.refresh(sub)
    if brand_catalog_dirty:
        clear_analysis_entities_cache(subject_id)
    return sub


@router.get("/{subject_id}/entities")
def list_subject_entities(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    return get_analysis_entities(subject)