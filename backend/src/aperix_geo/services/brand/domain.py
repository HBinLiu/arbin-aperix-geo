"""Resolve brand primary domains from cache or response text/URLs (no web search)."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.services.brand.cache import (
    get_brand_domain_cached,
    remember_brand_domain_cached,
)
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.utils.net import (
    brand_from,
    extract_urls,
    host_from,
    is_brand_domain,
)

_NEAR_WINDOW = 120
_DOMAIN_IN_TEXT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+)",
    re.IGNORECASE,
)


def other_entity_id(brand_name: str) -> str:
    key = (brand_name or "").strip().casefold()
    if not key:
        return "other:unknown"
    if len(key) <= 55:
        return f"other:{key}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"other:{digest}"


def _brand_near_span(text: str, brand: str, *, window: int = _NEAR_WINDOW) -> tuple[int, int] | None:
    lowered = text.casefold()
    needle = brand.strip().casefold()
    if not needle:
        return None
    idx = lowered.find(needle)
    if idx < 0:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(brand) + window)
    return start, end


def _domain_in_span(text: str, start: int, end: int) -> str:
    for match in _DOMAIN_IN_TEXT_RE.finditer(text[start:end]):
        domain = brand_from(match.group(1))
        if domain:
            return domain
    return ""


def _domain_from_urls_for_brand(text: str, brand: str, urls: list[str]) -> str:
    brand_key = brand.strip().casefold()
    span = _brand_near_span(text, brand)

    for url in urls:
        host = host_from(url)
        if not host:
            continue
        host_key = host.casefold()
        if brand_key and brand_key in host_key:
            domain = brand_from(host)
            if domain:
                return domain
        if span is not None and url in text[span[0] : span[1]]:
            domain = brand_from(host)
            if domain:
                return domain

    if span is not None:
        found = _domain_in_span(text, *span)
        if found:
            return found
    return ""


def extract_domain_from_text_for_brand(text: str, brand: str, urls: list[str] | None = None) -> str:
    if not text.strip() or not brand.strip():
        return ""
    merged_urls = list(dict.fromkeys([*(urls or []), *extract_urls(text)]))
    return _domain_from_urls_for_brand(text, brand, merged_urls)


def _verified_domain(candidate: str, brand: str) -> str:
    """Return registrable domain when DNS + host/homepage checks pass."""
    normalized = brand_from(candidate)
    if not normalized:
        return ""
    from aperix_geo.services.brand.verify import accept_discovered_domain

    if accept_discovered_domain(normalized, brand):
        return normalized
    return ""


def domain_plausibly_matches_brand(domain: str, brand: str) -> bool:
    """True when the registrable domain likely belongs to the brand (host label match)."""
    brand_key = (brand or "").strip().casefold()
    normalized = brand_from(domain)
    if not normalized or not brand_key:
        return False
    host = normalized.casefold()
    if brand_key in host:
        return True
    label = host.split(".", 1)[0]
    return brand_key == label or brand_key in label


def resolve_brand_domain(
    db: Session,
    *,
    subject_id: UUID,
    brand: str,
    raw_text: str = "",
    urls: list[str] | None = None,
    sync_ctx: BrandSyncContext | None = None,
) -> str:
    """Return primary domain from cache/catalog/text; empty when unresolved."""
    from aperix_geo.services.brand.resolve import find_brand_by_name_or_alias

    if sync_ctx is not None:
        memoized = sync_ctx.memoized_domain(brand)
        if memoized:
            return memoized

    cached = get_brand_domain_cached(subject_id=subject_id, brand=brand)
    if cached and is_brand_domain(cached):
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, cached)
        return cached

    if sync_ctx is not None:
        existing = sync_ctx.catalog.find_by_name_or_alias(brand)
    else:
        existing = find_brand_by_name_or_alias(db, subject_id=subject_id, brand=brand)
    if existing is not None and existing.domain:
        domain = brand_from(existing.domain)
        remember_brand_domain_cached(subject_id=subject_id, brand=brand, domain=domain)
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, domain)
        return domain

    from_text = _verified_domain(
        extract_domain_from_text_for_brand(raw_text, brand, urls),
        brand,
    )
    if from_text:
        remember_brand_domain_cached(subject_id=subject_id, brand=brand, domain=from_text)
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, from_text)
        return from_text

    return ""
