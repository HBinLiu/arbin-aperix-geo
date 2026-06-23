"""Async backfill of open-set brand domains after sampling persist."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import Brand, BrandSource, LLMResponse, LLMResponseSignal, Subject
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import resolve_brand_domain
from aperix_geo.services.brand.resolve import (
    find_brand_by_name,
    primary_domain_for_brand,
    resolve_or_create_brand,
)
from aperix_geo.utils.net import brand_from, is_brand_domain


def _clear_invalid_stored_domain(brand: Brand) -> None:
    stored = (brand.domain or "").strip()
    if stored and not brand_from(stored):
        brand.domain = ""


def _signal_needs_domain_backfill(db: Session, signal: LLMResponseSignal) -> bool:
    brand_name = (signal.entity_label or "").strip()
    if not brand_name:
        return False

    signal_raw = (signal.primary_domain or "").strip()
    signal_domain = brand_from(signal_raw)
    if signal_raw and not signal_domain:
        return True
    if not signal_domain:
        return True

    linked = db.get(Brand, signal.brand_id)
    if linked is None:
        return True

    _clear_invalid_stored_domain(linked)

    by_name = find_brand_by_name(db, subject_id=signal.subject_id, brand=brand_name)
    if by_name is None or by_name.id != signal.brand_id:
        return True

    brand_domain = brand_from(linked.domain or "")
    if brand_domain != signal_domain:
        return True

    return False


def backfill_brand_domain_for_response(db: Session, response_id: UUID) -> int:
    """Resolve missing other-brand domains via SearXNG; update tb_brands and signals."""
    row = db.get(LLMResponse, response_id)
    if row is None:
        return 0

    signals = list(
        db.execute(
            select(LLMResponseSignal).where(
                LLMResponseSignal.response_id == response_id,
                LLMResponseSignal.entity_kind == "other",
            )
        )
        .scalars()
        .all()
    )
    if not signals:
        return 0

    subject = db.get(Subject, signals[0].subject_id)
    if subject is None:
        return 0

    parsed = dict(row.parsed or {})
    raw_text = row.raw_text or ""
    urls = list(parsed.get("urls") or [])
    sync_ctx = BrandSyncContext.load(db, subject_id=subject.id)

    updated = 0
    for signal in signals:
        if not _signal_needs_domain_backfill(db, signal):
            continue

        brand_name = (signal.entity_label or "").strip()
        if not brand_name:
            continue

        signal_raw = (signal.primary_domain or "").strip()
        if signal_raw and not is_brand_domain(signal_raw):
            signal.primary_domain = ""

        linked = db.get(Brand, signal.brand_id)
        if linked is not None:
            _clear_invalid_stored_domain(linked)

        domain = resolve_brand_domain(
            db,
            subject_id=subject.id,
            brand=brand_name,
            raw_text=raw_text,
            urls=urls,
            allow_search=True,
            sync_ctx=sync_ctx,
        )
        if not domain:
            continue

        brand_row = resolve_or_create_brand(
            db,
            subject_id=subject.id,
            brand=brand_name,
            domain=domain,
            entity_kind="other",
            source=BrandSource.sampling_open_set,
            catalog=sync_ctx.catalog,
            open_set_brand=True,
        )
        signal.brand_id = brand_row.id
        signal.primary_domain = primary_domain_for_brand(brand_row)
        updated += 1

    return updated


def maybe_enqueue_brand_domain_backfill(response_id: UUID) -> None:
    """Enqueue Celery backfill when SearXNG is configured."""
    if not get_settings().searxng_base_url.strip():
        return

    from aperix_geo.utils.cache.redis_kv import redis_set_nx

    if not redis_set_nx(f"aperix:brand:backfill:{response_id}", ttl_s=3600):
        return

    from aperix_geo.tasks.brand import backfill_brand_domain

    backfill_brand_domain.delay(str(response_id))
