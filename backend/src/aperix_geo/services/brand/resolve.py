"""Tenant-scoped brand registry: resolve, upsert, domain backfill."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
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


def find_brand_by_domain(db: Session, *, tenant_id: UUID, domain: str) -> Brand | None:
    normalized = _normalize_domain(domain)
    if not normalized:
        return None
    return db.execute(
        select(Brand).where(Brand.tenant_id == tenant_id, Brand.domain == normalized)
    ).scalar_one_or_none()


def find_brand_by_name(db: Session, *, tenant_id: UUID, brand: str) -> Brand | None:
    name = (brand or "").strip()
    if not name:
        return None
    return db.execute(
        select(Brand).where(
            Brand.tenant_id == tenant_id,
            func.lower(Brand.brand) == name.casefold(),
        )
    ).scalar_one_or_none()


def find_brand_by_name_or_alias(db: Session, *, tenant_id: UUID, brand: str) -> Brand | None:
    row = find_brand_by_name(db, tenant_id=tenant_id, brand=brand)
    if row is not None:
        return row
    key = normalize_brand_key(brand)
    if not key:
        return None
    for candidate in db.execute(select(Brand).where(Brand.tenant_id == tenant_id)).scalars():
        for alias in candidate.aliases or []:
            if normalize_brand_key(str(alias)) == key:
                return candidate
    return None


def _find_brand(
    db: Session,
    *,
    tenant_id: UUID,
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
            row = find_brand_by_domain(db, tenant_id=tenant_id, domain=normalized_domain)
            if row is not None:
                return row
    if not brand.strip():
        return None
    if catalog is not None:
        return catalog.find_by_name_or_alias(brand)
    return find_brand_by_name_or_alias(db, tenant_id=tenant_id, brand=brand)


def _apply_domain_update(brand: Brand, domain: str, *, tenant_id: UUID | None = None) -> None:
    normalized = _normalize_domain(domain)
    if not normalized or brand.domain:
        return
    brand.domain = normalized
    if tenant_id is not None:
        remember_brand_row_domains(tenant_id=tenant_id, brand=brand)


def resolve_or_create_brand(
    db: Session,
    *,
    tenant_id: UUID,
    brand: str,
    domain: str = "",
    website_url: str = "",
    aliases: list[str] | None = None,
    summary: str = "",
    catalog: BrandCatalog | None = None,
) -> Brand:
    """Find or create a tenant-scoped brand row; merge aliases and backfill empty domain."""
    display_name = ensure_brand(brand, domain=domain)
    normalized_domain = _normalize_domain(domain)

    row = _find_brand(
        db,
        tenant_id=tenant_id,
        brand=display_name,
        domain=domain,
        catalog=catalog,
    )

    if row is None:
        row = Brand(
            tenant_id=tenant_id,
            brand=display_name,
            domain=normalized_domain,
            website_url=(website_url or "").strip(),
            aliases=_merge_aliases([], aliases),
            summary=(summary or "").strip(),
        )
        db.add(row)
        db.flush()
        if catalog is not None:
            catalog.register(row)
        remember_brand_row_domains(tenant_id=tenant_id, brand=row)
        return row

    if display_name and normalize_brand_key(display_name) != normalize_brand_key(row.brand):
        row.aliases = _merge_aliases(row.aliases or [], [display_name, *(aliases or [])])
    elif aliases:
        row.aliases = _merge_aliases(row.aliases or [], aliases)

    if (website_url or "").strip() and not row.website_url:
        row.website_url = website_url.strip()
    if (summary or "").strip() and not row.summary:
        row.summary = summary.strip()

    _apply_domain_update(row, domain, tenant_id=tenant_id)
    if not row.brand:
        row.brand = display_name
    db.flush()
    if catalog is not None:
        catalog.register(row)
    remember_brand_row_domains(tenant_id=tenant_id, brand=row)
    return row


def primary_domain_for_brand(brand: Brand) -> str:
    return _normalize_domain(brand.domain)
