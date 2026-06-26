"""Subject-scoped brand registry: resolve, upsert, domain backfill."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.cache import remember_brand_row_domains
from aperix_geo.services.brand.catalog import BrandCatalog
from aperix_geo.utils.net import brand_from, ensure_brand, is_brand_domain


def normalize_brand_key(name: str) -> str:
    return (name or "").strip().casefold()


def _merge_aliases(existing: list[Any], extra: list[str] | None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*existing, *(extra or [])]:
        text = str(value or "").strip()
        if not text:
            continue
        key = normalize_brand_key(text)
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)
    return merged


def merge_brand_aliases(existing: list[Any], extra: list[str] | None) -> list[str]:
    return _merge_aliases(existing, extra)


def find_brand_by_domain(db: Session, *, subject_id: UUID, domain: str) -> Brand | None:
    normalized = brand_from(domain)
    if not normalized:
        return None
    return db.execute(
        select(Brand).where(Brand.subject_id == subject_id, Brand.domain == normalized)
    ).scalar_one_or_none()


def find_brand_by_name(db: Session, *, subject_id: UUID, brand: str) -> Brand | None:
    name = (brand or "").strip()
    if not name:
        return None
    return db.execute(
        select(Brand).where(
            Brand.subject_id == subject_id,
            func.lower(Brand.brand) == name.casefold(),
        )
    ).scalar_one_or_none()


def find_brand_by_name_or_alias(db: Session, *, subject_id: UUID, brand: str) -> Brand | None:
    row = find_brand_by_name(db, subject_id=subject_id, brand=brand)
    if row is not None:
        return row
    key = normalize_brand_key(brand)
    if not key:
        return None
    for candidate in db.execute(select(Brand).where(Brand.subject_id == subject_id)).scalars():
        for alias in candidate.aliases or []:
            if normalize_brand_key(str(alias)) == key:
                return candidate
    return None


def find_brand_by_entity_id(db: Session, *, subject_id: UUID, entity_id: str) -> Brand | None:
    key = (entity_id or "").strip()
    if not key:
        return None
    return db.execute(
        select(Brand).where(Brand.subject_id == subject_id, Brand.entity_id == key)
    ).scalar_one_or_none()


def _find_brand(
    db: Session,
    *,
    subject_id: UUID,
    brand: str,
    domain: str,
    catalog: BrandCatalog | None,
    match_by_domain: bool = True,
    canonical_name_only: bool = False,
) -> Brand | None:
    normalized_domain = brand_from(domain) if match_by_domain else ""
    if normalized_domain:
        if catalog is not None:
            row = catalog.find_by_domain(normalized_domain)
            if row is not None:
                return row
        else:
            row = find_brand_by_domain(db, subject_id=subject_id, domain=normalized_domain)
            if row is not None:
                return row
    if not brand.strip():
        return None
    if canonical_name_only:
        if catalog is not None:
            return catalog.find_by_canonical_name(brand)
        return find_brand_by_name(db, subject_id=subject_id, brand=brand)
    if catalog is not None:
        return catalog.find_by_name_or_alias(brand)
    return find_brand_by_name_or_alias(db, subject_id=subject_id, brand=brand)


def _clear_invalid_stored_domain(brand: Brand) -> None:
    stored = (brand.domain or "").strip()
    if stored and not brand_from(stored):
        brand.domain = ""


def _apply_domain_update(brand: Brand, domain: str, *, subject_id: UUID | None = None) -> None:
    normalized = brand_from(domain)
    if not normalized:
        return
    stored = (brand.domain or "").strip()
    if stored and is_brand_domain(stored):
        current = brand_from(stored)
        if current == normalized:
            return
        return
    brand.domain = normalized
    if subject_id is not None:
        remember_brand_row_domains(subject_id=subject_id, brand=brand)


def resolve_or_create_brand(
    db: Session,
    *,
    subject_id: UUID,
    brand: str,
    domain: str = "",
    website_url: str = "",
    aliases: list[str] | None = None,
    summary: str = "",
    entity_id: str = "",
    entity_kind: str = "other",
    source: str = "",
    catalog: BrandCatalog | None = None,
    open_set_brand: bool = False,
) -> Brand:
    """Find or create a subject-scoped brand row; merge aliases and backfill empty domain."""
    display_name = ensure_brand(brand, domain=domain)
    normalized_domain = brand_from(domain)
    match_by_domain = not open_set_brand
    canonical_name_only = open_set_brand
    entity_key = (entity_id or "").strip()

    row = None
    if entity_key:
        row = find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_key)
    if row is None:
        row = _find_brand(
            db,
            subject_id=subject_id,
            brand=display_name,
            domain=domain,
            catalog=catalog,
            match_by_domain=match_by_domain,
            canonical_name_only=canonical_name_only,
        )

    if row is None:
        created = Brand(
            subject_id=subject_id,
            entity_id=entity_key,
            entity_kind=entity_kind,
            brand=display_name,
            domain=normalized_domain,
            website_url=(website_url or "").strip(),
            aliases=_merge_aliases([], aliases),
            summary=(summary or "").strip(),
            source=(source or "").strip(),
        )
        db.add(created)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            if inspect(created).session is db:
                db.expunge(created)
            row = None
            if entity_key:
                row = find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_key)
            if row is None:
                row = _find_brand(
                    db,
                    subject_id=subject_id,
                    brand=display_name,
                    domain=domain,
                    catalog=catalog,
                    match_by_domain=match_by_domain,
                    canonical_name_only=canonical_name_only,
                )
            if row is None:
                row = find_brand_by_name(db, subject_id=subject_id, brand=display_name)
            if row is None:
                raise
        else:
            if catalog is not None:
                catalog.register(created)
            remember_brand_row_domains(subject_id=subject_id, brand=created)
            return created

    _clear_invalid_stored_domain(row)

    if entity_key:
        row.entity_id = entity_key
    if entity_kind and row.entity_kind == "other" and entity_kind != "other":
        row.entity_kind = entity_kind
    if (source or "").strip() and not row.source:
        row.source = source.strip()

    if not open_set_brand:
        if display_name and normalize_brand_key(display_name) != normalize_brand_key(row.brand):
            row.aliases = _merge_aliases(row.aliases or [], [display_name, *(aliases or [])])
        elif aliases:
            row.aliases = _merge_aliases(row.aliases or [], aliases)
    elif aliases:
        row.aliases = _merge_aliases(row.aliases or [], aliases)

    if (website_url or "").strip() and not row.website_url:
        row.website_url = website_url.strip()
    if (summary or "").strip() and not row.summary:
        row.summary = summary.strip()

    _apply_domain_update(row, domain, subject_id=subject_id)
    if not row.brand:
        row.brand = display_name
    row_id = row.id
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        row = db.get(Brand, row_id) or (
            find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_key)
            if entity_key
            else None
        )
        if row is None:
            row = _find_brand(
                db,
                subject_id=subject_id,
                brand=display_name,
                domain=domain,
                catalog=catalog,
                match_by_domain=match_by_domain,
                canonical_name_only=canonical_name_only,
            )
        if row is None:
            raise
    if catalog is not None:
        catalog.register(row)
    remember_brand_row_domains(subject_id=subject_id, brand=row)
    return row


def primary_domain_for_brand(brand: Brand) -> str:
    return brand_from(brand.domain)
