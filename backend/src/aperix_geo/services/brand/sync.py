"""Upsert tenant brands from neutral entity descriptors."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import resolve_brand_domain
from aperix_geo.services.brand.resolve import resolve_or_create_brand
from aperix_geo.services.brand.types import BrandSyncEntity


def sync_brand_for_entity(
    db: Session,
    *,
    tenant_id: UUID,
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
            tenant_id=tenant_id,
            brand=entity.brand or entity.entity_label,
            domain=entity.domain,
            website_url=entity.website_url,
            aliases=list(entity.aliases),
            catalog=catalog,
        )

    if entity.entity_kind == "competitor":
        return resolve_or_create_brand(
            db,
            tenant_id=tenant_id,
            brand=entity.brand or entity.entity_label,
            domain=entity.domain,
            website_url=entity.website_url,
            aliases=list(entity.aliases),
            summary=entity.summary,
            catalog=catalog,
        )

    domain = entity.domain or resolve_brand_domain(
        db,
        tenant_id=tenant_id,
        brand=entity.entity_label,
        raw_text=raw_text,
        urls=urls,
        allow_search=allow_search,
        sync_ctx=sync_ctx,
    )
    return resolve_or_create_brand(
        db,
        tenant_id=tenant_id,
        brand=entity.entity_label,
        domain=domain,
        catalog=catalog,
    )


def sync_brands_for_entities(
    db: Session,
    *,
    tenant_id: UUID,
    entities: list[BrandSyncEntity],
    raw_text: str = "",
    urls: list[str] | None = None,
    allow_search: bool = True,
) -> dict[str, Brand]:
    sync_ctx = BrandSyncContext.load(db, tenant_id=tenant_id)
    brands: dict[str, Brand] = {}
    for entity in entities:
        brands[entity.entity_id] = sync_brand_for_entity(
            db,
            tenant_id=tenant_id,
            entity=entity,
            raw_text=raw_text,
            urls=urls,
            allow_search=allow_search,
            sync_ctx=sync_ctx,
        )
    return brands
