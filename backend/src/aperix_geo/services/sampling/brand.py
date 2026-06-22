"""Persist ABSA open-set brands into tb_brands during sampling parse."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from aperix_geo.db.models import BrandSource, Subject
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import extract_domain_from_text_for_brand, resolve_brand_domain
from aperix_geo.services.brand.resolve import resolve_or_create_brand
from aperix_geo.utils.domains import registrable_domain

logger = logging.getLogger(__name__)


def persist_open_brands_from_absa(
    db: Session,
    *,
    subject: Subject,
    response_absa: dict[str, Any],
    raw_text: str,
    url_hosts: list[str] | None = None,
) -> int:
    """Upsert subject-scoped open-set brand rows from ABSA output (no cross-validation)."""
    others = dict(response_absa.get("other_brands_sentiment_absa") or {})
    if not others:
        return 0

    own_name = (subject.brand or "").strip().casefold()
    configured_names = {
        (c.brand or "").strip().casefold()
        for c in (subject.competitors or [])
        if (c.brand or "").strip()
    }
    configured_domains = {
        registrable_domain(c.domain)
        for c in (subject.competitors or [])
        if c.domain and registrable_domain(c.domain)
    }

    sync_ctx = BrandSyncContext.load(db, subject_id=subject.id)
    urls = list(url_hosts or [])
    persisted = 0

    for name, entry in others.items():
        label = str(name or "").strip()
        if not label or not isinstance(entry, dict) or not entry.get("mentioned"):
            continue
        label_key = label.casefold()
        if label_key == own_name or label_key in configured_names:
            continue

        domain = extract_domain_from_text_for_brand(raw_text, label, urls)
        if not domain:
            domain = resolve_brand_domain(
                db,
                subject_id=subject.id,
                brand=label,
                raw_text=raw_text,
                urls=urls,
                allow_search=False,
                sync_ctx=sync_ctx,
            )
        domain_key = registrable_domain(domain) if domain else ""
        if domain_key and domain_key in configured_domains:
            continue

        resolve_or_create_brand(
            db,
            subject_id=subject.id,
            brand=label,
            domain=domain or "",
            entity_kind="other",
            source=BrandSource.sampling_open_set,
            catalog=sync_ctx.catalog,
        )
        persisted += 1
        logger.debug(
            "开集品牌已写入 tb_brands subject=%s brand=%r domain=%s",
            subject.id,
            label,
            domain_key or "(empty)",
        )

    if persisted:
        db.flush()
    return persisted
