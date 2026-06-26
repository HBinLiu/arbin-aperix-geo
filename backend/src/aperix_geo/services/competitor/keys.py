"""Normalized match keys for configured competitors (domain-first, else brand)."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.utils.net import registrable_from


def competitor_match_key(*, domain: str, brand: str) -> str | None:
    domain_key = registrable_from(domain) if domain else ""
    if domain_key:
        return f"d:{domain_key}"
    brand_key = normalize_brand_key(brand)
    if brand_key:
        return f"b:{brand_key}"
    return None


def find_competitor_conflict(
    subject: Subject,
    *,
    domain: str,
    brand: str,
    exclude_competitor_id: UUID | None = None,
) -> str | None:
    """Return a user-facing conflict reason, or None when no duplicate exists."""
    domain_key = registrable_from(domain) if domain else ""
    brand_key = normalize_brand_key(brand)
    for existing in subject.competitors or []:
        if exclude_competitor_id is not None and existing.id == exclude_competitor_id:
            continue
        existing_domain = registrable_from(existing.domain) if existing.domain else ""
        if domain_key and existing_domain and domain_key == existing_domain:
            return "该域名已是配置竞品"
        existing_brand_key = normalize_brand_key(existing.brand)
        if brand_key and existing_brand_key and brand_key == existing_brand_key:
            return "该品牌已是配置竞品"
    return None
