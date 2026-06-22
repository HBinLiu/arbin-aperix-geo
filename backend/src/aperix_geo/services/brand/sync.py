"""Upsert subject brands from neutral entity descriptors."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, BrandSource, Competitor, Subject
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import resolve_brand_domain
from aperix_geo.services.brand.resolve import resolve_or_create_brand
from aperix_geo.services.brand.types import BrandSyncEntity


def sync_brand_for_entity(
    db: Session,
    *,
    subject_id: UUID,
    entity: BrandSyncEntity,
    raw_text: str = "",
    urls: list[str] | None = None,
    allow_search: bool = True,
    sync_ctx: BrandSyncContext | None = None,
) -> Brand:
    catalog = sync_ctx.catalog if sync_ctx is not None else None

    if entity.entity_kind == "own":
        return resolve_or_create_brand(
            db,
            subject_id=subject_id,
            brand=entity.brand or entity.entity_label,
            domain=entity.domain,
            website_url=entity.website_url,
            aliases=list(entity.aliases),
            entity_kind="own",
            source=entity.source or BrandSource.setup,
            catalog=catalog,
        )

    if entity.entity_kind == "competitor":
        return resolve_or_create_brand(
            db,
            subject_id=subject_id,
            brand=entity.brand or entity.entity_label,
            domain=entity.domain,
            website_url=entity.website_url,
            aliases=list(entity.aliases),
            summary=entity.summary,
            entity_kind="competitor",
            source=entity.source or BrandSource.setup,
            cross_validate_score=entity.cross_validate_score,
            cross_validate_reason=entity.cross_validate_reason,
            catalog=catalog,
        )

    domain = entity.domain or resolve_brand_domain(
        db,
        subject_id=subject_id,
        brand=entity.entity_label,
        raw_text=raw_text,
        urls=urls,
        allow_search=allow_search,
        sync_ctx=sync_ctx,
    )
    return resolve_or_create_brand(
        db,
        subject_id=subject_id,
        brand=entity.entity_label,
        domain=domain,
        entity_kind="other",
        source=entity.source or BrandSource.sampling_open_set,
        cross_validate_score=entity.cross_validate_score,
        cross_validate_reason=entity.cross_validate_reason,
        catalog=catalog,
    )


_ENTITY_KIND_ORDER = {"own": 0, "competitor": 1, "other": 2}


def _brand_sync_sort_key(entity: BrandSyncEntity) -> tuple[int, str]:
    return (_ENTITY_KIND_ORDER.get(entity.entity_kind, 9), entity.entity_id)


def sync_brands_for_entities(
    db: Session,
    *,
    subject_id: UUID,
    entities: list[BrandSyncEntity],
    raw_text: str = "",
    urls: list[str] | None = None,
    allow_search: bool = True,
) -> dict[str, Brand]:
    sync_ctx = BrandSyncContext.load(db, subject_id=subject_id)
    brands: dict[str, Brand] = {}
    for entity in sorted(entities, key=_brand_sync_sort_key):
        brands[entity.entity_id] = sync_brand_for_entity(
            db,
            subject_id=subject_id,
            entity=entity,
            raw_text=raw_text,
            urls=urls,
            allow_search=allow_search,
            sync_ctx=sync_ctx,
        )
    return brands


def sync_subject_brands_from_setup(db: Session, *, subject: Subject) -> dict[str, Brand]:
    """Upsert own + configured competitor rows after setup finalize."""
    from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, own_entity

    own = own_entity(subject)
    display = (subject.brand or own.label).strip() or own.label
    entities: list[BrandSyncEntity] = [
        BrandSyncEntity(
            entity_id=OWN_ENTITY_ID,
            entity_kind="own",
            entity_label=own.label,
            brand=display,
            domain=subject.domain or "",
            website_url=subject.website_url or "",
            aliases=tuple(str(x) for x in (subject.aliases or []) if str(x).strip()),
            source=BrandSource.setup,
        )
    ]
    for competitor in subject.competitors or []:
        entities.append(
            BrandSyncEntity(
                entity_id=str(competitor.id),
                entity_kind="competitor",
                entity_label=(competitor.brand or competitor.domain or "").strip(),
                brand=(competitor.brand or "").strip(),
                domain=competitor.domain or "",
                website_url=competitor.website_url or "",
                aliases=tuple(str(x) for x in (competitor.aliases or []) if str(x).strip()),
                summary=(competitor.summary or "").strip(),
                source=BrandSource.setup,
                cross_validate_score=competitor.cross_validate_score,
                cross_validate_reason=competitor.cross_validate_reason or "",
            )
        )
    return sync_brands_for_entities(db, subject_id=subject.id, entities=entities, allow_search=False)
