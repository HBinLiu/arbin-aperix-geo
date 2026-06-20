"""Subject-scoped brand registry: resolve, upsert, domain backfill."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.cache import remember_brand_row_domains
from aperix_geo.services.brand.catalog import BrandCatalog
from aperix_geo.utils.domains import ensure_brand, registrable_domain


def normalize_brand_key(name: str) -> str:
    return (name or "").strip().casefold()


def _normalize_domain(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    return registrable_domain(text) or text


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


def find_brand_by_domain(db: Session, *, subject_id: UUID, domain: str) -> Brand | None:
    normalized = _normalize_domain(domain)
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


def _find_brand(
    db: Session,
    *,
    subject_id: UUID,
    brand: str,
    domain: str,
    catalog: BrandCatalog | None,
) -> Brand | None:
    normalized_domain = _normalize_domain(domain)
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
    if catalog is not None:
        return catalog.find_by_name_or_alias(brand)
    return find_brand_by_name_or_alias(db, subject_id=subject_id, brand=brand)


def _apply_domain_update(brand: Brand, domain: str, *, subject_id: UUID | None = None) -> None:
    normalized = _normalize_domain(domain)
    if not normalized or brand.domain:
        return
    brand.domain = normalized
    if subject_id is not None:
        remember_brand_row_domains(subject_id=subject_id, brand=brand)


def _apply_cross_validate_fields(
    brand: Brand,
    *,
    cross_validate_score: float | None,
    cross_validate_reason: str | None,
) -> None:
    if cross_validate_score is None:
        return
    brand.cross_validate_score = cross_validate_score
    brand.cross_validate_reason = (cross_validate_reason or "").strip()
    brand.cross_validated_at = datetime.now(UTC)


def resolve_or_create_brand(
    db: Session,
    *,
    subject_id: UUID,
    brand: str,
    domain: str = "",
    website_url: str = "",
    aliases: list[str] | None = None,
    summary: str = "",
    entity_kind: str = "other",
    source: str = "",
    cross_validate_score: float | None = None,
    cross_validate_reason: str | None = None,
    catalog: BrandCatalog | None = None,
) -> Brand:
    """Find or create a subject-scoped brand row; merge aliases and backfill empty domain."""
    display_name = ensure_brand(brand, domain=domain)
    normalized_domain = _normalize_domain(domain)

    row = _find_brand(
        db,
        subject_id=subject_id,
        brand=display_name,
        domain=domain,
        catalog=catalog,
    )

    if row is None:
        created = Brand(
            subject_id=subject_id,
            entity_kind=entity_kind,
            brand=display_name,
            domain=normalized_domain,
            website_url=(website_url or "").strip(),
            aliases=_merge_aliases([], aliases),
            summary=(summary or "").strip(),
            source=(source or "").strip(),
        )
        _apply_cross_validate_fields(
            created,
            cross_validate_score=cross_validate_score,
            cross_validate_reason=cross_validate_reason,
        )
        db.add(created)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            db.expunge(created)
            row = _find_brand(
                db,
                subject_id=subject_id,
                brand=display_name,
                domain=domain,
                catalog=catalog,
            )
            if row is None:
                raise
        else:
            if catalog is not None:
                catalog.register(created)
            remember_brand_row_domains(subject_id=subject_id, brand=created)
            return created

    if entity_kind and row.entity_kind == "other" and entity_kind != "other":
        row.entity_kind = entity_kind
    if (source or "").strip() and not row.source:
        row.source = source.strip()

    if display_name and normalize_brand_key(display_name) != normalize_brand_key(row.brand):
        row.aliases = _merge_aliases(row.aliases or [], [display_name, *(aliases or [])])
    elif aliases:
        row.aliases = _merge_aliases(row.aliases or [], aliases)

    if (website_url or "").strip() and not row.website_url:
        row.website_url = website_url.strip()
    if (summary or "").strip() and not row.summary:
        row.summary = summary.strip()

    _apply_domain_update(row, domain, subject_id=subject_id)
    if not row.brand:
        row.brand = display_name
    _apply_cross_validate_fields(
        row,
        cross_validate_score=cross_validate_score,
        cross_validate_reason=cross_validate_reason,
    )
    row_id = row.id
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        row = db.get(Brand, row_id) or _find_brand(
            db,
            subject_id=subject_id,
            brand=display_name,
            domain=domain,
            catalog=catalog,
        )
        if row is None:
            raise
    if catalog is not None:
        catalog.register(row)
    remember_brand_row_domains(subject_id=subject_id, brand=row)
    return row


def primary_domain_for_brand(brand: Brand) -> str:
    return _normalize_domain(brand.domain)


def brand_passes_cross_validate(brand: Brand, *, min_score: float) -> bool:
    score = brand.cross_validate_score
    return score is not None and score >= min_score
