"""Resolve brand primary domains from cache, text URLs, or search."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.cache import (
    get_brand_domain_cached,
    remember_brand_domain_cached,
)
from aperix_geo.config import get_settings
from aperix_geo.services.competitor.filters import SKIP_DOMAINS
from aperix_geo.services.searxng import SearchHit, search_text
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import extract_urls, hostname_from_url

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


def _normalize_domain(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    return registrable_domain(text) or text


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
        domain = _normalize_domain(match.group(1))
        if domain:
            return domain
    return ""


def _domain_from_urls_for_brand(text: str, brand: str, urls: list[str]) -> str:
    span = _brand_near_span(text, brand)
    if span is not None:
        found = _domain_in_span(text, *span)
        if found:
            return found

    brand_key = brand.strip().casefold()
    for url in urls:
        host = hostname_from_url(url) or ""
        if not host:
            continue
        host_key = host.casefold()
        if brand_key and brand_key in host_key:
            return _normalize_domain(host)
        if span is not None and url in text[span[0] : span[1]]:
            return _normalize_domain(host)
    return ""


def extract_domain_from_text_for_brand(text: str, brand: str, urls: list[str] | None = None) -> str:
    if not text.strip() or not brand.strip():
        return ""
    merged_urls = list(dict.fromkeys([*(urls or []), *extract_urls(text)]))
    return _domain_from_urls_for_brand(text, brand, merged_urls)


def _is_usable_brand_domain(domain: str) -> bool:
    normalized = _normalize_domain(domain)
    if not normalized:
        return False
    if normalized in SKIP_DOMAINS:
        return False
    return True


def _brand_match_key(brand: str) -> str:
    return brand.strip().casefold()


def _domain_hosts_brand(domain: str, brand_key: str) -> bool:
    if not brand_key or not domain:
        return False
    host = domain.casefold()
    if brand_key in host:
        return True
    label = host.split(".", 1)[0]
    return brand_key == label or brand_key in label


def _text_mentions_brand(text: str, brand_key: str) -> bool:
    return bool(brand_key and brand_key in text.casefold())


def _pick_brand_domain_from_search_hits(brand: str, hits: list[SearchHit]) -> str:
    """Pick the best official-domain candidate; empty when nothing matches the brand."""
    brand_key = _brand_match_key(brand)
    if not brand_key:
        return ""

    for hit in hits:
        domain = _normalize_domain(hostname_from_url(hit.url) or "")
        if not _is_usable_brand_domain(domain):
            continue
        if _domain_hosts_brand(domain, brand_key):
            return domain

    for hit in hits:
        domain = _normalize_domain(hostname_from_url(hit.url) or "")
        if not _is_usable_brand_domain(domain):
            continue
        if _text_mentions_brand(hit.title, brand_key):
            return domain

    return ""


def search_brand_official_domain(brand: str) -> str:
    name = (brand or "").strip()
    if not name:
        return ""
    if not get_settings().searxng_base_url.strip():
        return ""

    for query in (f"{name} 官网", f"{name} official site"):
        domain = _pick_brand_domain_from_search_hits(name, search_text(query, max_results=5))
        if domain:
            return domain
    return ""


def resolve_brand_domain(
    db: Session,
    *,
    tenant_id: UUID,
    brand: str,
    raw_text: str = "",
    urls: list[str] | None = None,
    allow_search: bool = True,
    sync_ctx: BrandSyncContext | None = None,
) -> str:
    """Return primary domain; empty when unresolved."""
    from aperix_geo.services.brand.resolve import find_brand_by_name_or_alias

    if sync_ctx is not None:
        memoized = sync_ctx.memoized_domain(brand)
        if memoized:
            return memoized

    cached = get_brand_domain_cached(tenant_id=tenant_id, brand=brand)
    if cached:
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, cached)
        return cached

    if sync_ctx is not None:
        existing = sync_ctx.catalog.find_by_name_or_alias(brand)
    else:
        existing = find_brand_by_name_or_alias(db, tenant_id=tenant_id, brand=brand)
    if existing is not None and existing.domain:
        domain = _normalize_domain(existing.domain)
        remember_brand_domain_cached(tenant_id=tenant_id, brand=brand, domain=domain)
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, domain)
        return domain

    from_text = extract_domain_from_text_for_brand(raw_text, brand, urls)
    if from_text:
        remember_brand_domain_cached(tenant_id=tenant_id, brand=brand, domain=from_text)
        if sync_ctx is not None:
            sync_ctx.remember_domain(brand, from_text)
        return from_text

    if allow_search:
        from_search = search_brand_official_domain(brand)
        if from_search:
            remember_brand_domain_cached(tenant_id=tenant_id, brand=brand, domain=from_search)
            if sync_ctx is not None:
                sync_ctx.remember_domain(brand, from_search)
            return from_search

    return ""
