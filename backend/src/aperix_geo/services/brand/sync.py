"""Upsert subject brands from neutral entity descriptors."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, BrandSource, Competitor, EntityKind, Subject
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import resolve_brand_domain
from aperix_geo.services.brand.cache import remember_brand_row_domains
from aperix_geo.services.brand.resolve import (
    find_brand_by_domain,
    find_brand_by_entity_id,
    find_brand_by_name_or_alias,
    resolve_or_create_brand,
)
from aperix_geo.services.brand.types import BrandSyncEntity
from aperix_geo.utils.net import ensure_brand, registrable_from


def _apply_brand_fields(
    row: Brand,
    *,
    entity_id: str,
    entity_kind: str,
    brand: str,
    domain_key: str,
    website_url: str,
    aliases: list[str],
    summary: str,
    source: str,
) -> None:
    row.entity_id = entity_id
    row.entity_kind = entity_kind
    row.brand = brand
    row.domain = domain_key
    row.website_url = website_url
    row.aliases = aliases
    row.summary = summary
    if source and not row.source:
        row.source = source


def _release_domain_from_other_brand(
    db: Session,
    *,
    subject_id: UUID,
    domain_key: str,
    keep_id: UUID,
) -> None:
    if not domain_key:
        return
    holder = find_brand_by_domain(db, subject_id=subject_id, domain=domain_key)
    if holder is None or holder.id == keep_id:
        return
    holder.domain = ""
    with db.begin_nested():
        db.flush()


def _find_brand_for_force_sync(
    db: Session,
    *,
    subject_id: UUID,
    entity_id: str,
    domain_key: str = "",
) -> Brand | None:
    row = find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_id)
    if row is not None:
        return row
    if domain_key:
        return find_brand_by_domain(db, subject_id=subject_id, domain=domain_key)
    return None


def _force_write_brand_row(
    db: Session,
    *,
    subject_id: UUID,
    row: Brand | None,
    entity_id: str,
    entity_kind: str,
    brand: str,
    domain_key: str,
    website_url: str,
    aliases: list[str],
    summary: str,
    source: str,
) -> Brand:
    domain_holder = (
        find_brand_by_domain(db, subject_id=subject_id, domain=domain_key) if domain_key else None
    )
    entity_holder = (
        find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_id) if entity_id else None
    )

    if entity_holder is not None:
        target = entity_holder
    elif row is not None:
        target = row
    elif domain_holder is not None:
        target = domain_holder
    else:
        target = Brand(
            subject_id=subject_id,
            entity_id=entity_id,
            entity_kind=entity_kind,
            brand=brand,
            domain=domain_key,
            website_url=website_url,
            aliases=aliases,
            summary=summary,
            source=source,
        )
        db.add(target)

    created_new = inspect(target).transient

    if domain_key and domain_holder is not None and domain_holder.id != target.id:
        _release_domain_from_other_brand(
            db,
            subject_id=subject_id,
            domain_key=domain_key,
            keep_id=target.id,
        )

    _apply_brand_fields(
        target,
        entity_id=entity_id,
        entity_kind=entity_kind,
        brand=brand,
        domain_key=domain_key,
        website_url=website_url,
        aliases=aliases,
        summary=summary,
        source=source,
    )

    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        if created_new and inspect(target).session is db:
            db.expunge(target)
        retry = _find_brand_for_force_sync(
            db,
            subject_id=subject_id,
            entity_id=entity_id,
            domain_key=domain_key,
        )
        if retry is None:
            raise
        if domain_key:
            _release_domain_from_other_brand(
                db,
                subject_id=subject_id,
                domain_key=domain_key,
                keep_id=retry.id,
            )
        _apply_brand_fields(
            retry,
            entity_id=entity_id,
            entity_kind=entity_kind,
            brand=brand,
            domain_key=domain_key,
            website_url=website_url,
            aliases=aliases,
            summary=summary,
            source=source,
        )
        target = retry
        with db.begin_nested():
            db.flush()

    remember_brand_row_domains(subject_id=subject_id, brand=target)
    return target


def force_sync_own_brand_from_subject(
    db: Session,
    *,
    subject: Subject,
) -> Brand:
    """Overwrite tb_brands own row from subject fields (source of truth)."""
    from aperix_geo.services.analysis.entity import own_entity

    own = own_entity(subject)
    row = find_brand_by_entity_id(db, subject_id=subject.id, entity_id=OWN_ENTITY_ID)

    display_brand = ensure_brand(subject.brand or own.label, domain=subject.domain or "")
    domain_key = registrable_from(subject.domain) if subject.domain else ""
    website_url = (subject.website_url or "").strip()
    aliases = [str(alias).strip() for alias in (subject.aliases or []) if str(alias).strip()]
    summary = (subject.profile_summary or "").strip()

    return _force_write_brand_row(
        db,
        subject_id=subject.id,
        row=row,
        entity_id=OWN_ENTITY_ID,
        entity_kind=EntityKind.own.value,
        brand=display_brand,
        domain_key=domain_key,
        website_url=website_url,
        aliases=aliases,
        summary=summary,
        source=BrandSource.setup,
    )


def force_sync_brand_from_competitor(
    db: Session,
    *,
    subject_id: UUID,
    competitor: Competitor,
) -> Brand:
    """Overwrite tb_brands fields from a configured competitor (source of truth)."""
    entity_id = str(competitor.id)
    domain_key = registrable_from(competitor.domain) if competitor.domain else ""
    row = _find_brand_for_force_sync(
        db,
        subject_id=subject_id,
        entity_id=entity_id,
        domain_key=domain_key,
    )

    display_brand = ensure_brand(competitor.brand or "", domain=competitor.domain or "")
    website_url = (competitor.website_url or "").strip()
    aliases = [str(alias).strip() for alias in (competitor.aliases or []) if str(alias).strip()]
    summary = (competitor.summary or "").strip()

    return _force_write_brand_row(
        db,
        subject_id=subject_id,
        row=row,
        entity_id=entity_id,
        entity_kind=EntityKind.competitor.value,
        brand=display_brand,
        domain_key=domain_key,
        website_url=website_url,
        aliases=aliases,
        summary=summary,
        source=BrandSource.setup,
    )


def sync_brand_for_entity(
    db: Session,
    *,
    subject_id: UUID,
    entity: BrandSyncEntity,
    raw_text: str = "",
    urls: list[str] | None = None,
    sync_ctx: BrandSyncContext | None = None,
) -> Brand:
    catalog = sync_ctx.catalog if sync_ctx is not None else None

    if entity.entity_kind == "own":
        return resolve_or_create_brand(
            db,
            subject_id=subject_id,
            entity_id=entity.entity_id,
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
            entity_id=entity.entity_id,
            brand=entity.brand or entity.entity_label,
            domain=entity.domain,
            website_url=entity.website_url,
            aliases=list(entity.aliases),
            summary=entity.summary,
            entity_kind="competitor",
            source=entity.source or BrandSource.setup,
            catalog=catalog,
        )

    domain = entity.domain or resolve_brand_domain(
        db,
        subject_id=subject_id,
        brand=entity.entity_label,
        raw_text=raw_text,
        urls=urls,
        sync_ctx=sync_ctx,
    )
    return resolve_or_create_brand(
        db,
        subject_id=subject_id,
        brand=entity.entity_label,
        domain=domain,
        entity_kind="other",
        source=entity.source or BrandSource.sampling_open_set,
        catalog=catalog,
        open_set_brand=True,
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
) -> dict[str, Brand]:
    sync_ctx = BrandSyncContext.load(db, subject_id=subject_id)
    brands: dict[str, Brand] = {}
    for entity in sorted(entities, key=_brand_sync_sort_key):
        try:
            brands[entity.entity_id] = sync_brand_for_entity(
                db,
                subject_id=subject_id,
                entity=entity,
                raw_text=raw_text,
                urls=urls,
                sync_ctx=sync_ctx,
            )
        except IntegrityError:
            db.rollback()
            fallback = find_brand_by_name_or_alias(
                db,
                subject_id=subject_id,
                brand=entity.brand or entity.entity_label,
            )
            if fallback is None:
                raise
            brands[entity.entity_id] = fallback
    return brands


def sync_subject_brands_from_setup(db: Session, *, subject: Subject) -> dict[str, Brand]:
    """Upsert own + configured competitor rows after setup finalize."""
    brands: dict[str, Brand] = {
        OWN_ENTITY_ID: force_sync_own_brand_from_subject(db, subject=subject),
    }
    for competitor in subject.competitors or []:
        brands[str(competitor.id)] = force_sync_brand_from_competitor(
            db,
            subject_id=subject.id,
            competitor=competitor,
        )
    return brands
