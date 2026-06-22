"""Global URL-scoped citation page metadata cache (parsed CitationPageMeta)."""

from __future__ import annotations

from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.utils.cache import TieredJsonCache
from aperix_geo.utils.url import normalize_crawl_cache_url

_STORE = TieredJsonCache(
    redis_prefix="aperix:sampling:url_page_meta:v1:",
    l1_max_entries=2048,
    use_remaining_ttl=False,
)


def _url_meta_cache_ttl_s() -> int:
    return get_settings().page_crawl_cache_ttl_s


def get_url_citation_page(url: str) -> dict[str, Any] | None:
    key = normalize_crawl_cache_url(url)
    if not key:
        return None
    ttl_s = _url_meta_cache_ttl_s()
    if ttl_s <= 0:
        return None
    return _STORE.get(
        key,
        default_ttl_s=ttl_s,
        is_valid=lambda payload: bool(payload.get("url")),
    )


def set_url_citation_page(payload: dict[str, Any], *, ttl_s: int | None = None) -> None:
    url = str(payload.get("url") or "").strip()
    if not url:
        return
    effective_ttl = _url_meta_cache_ttl_s() if ttl_s is None else ttl_s
    if effective_ttl <= 0:
        return
    key = normalize_crawl_cache_url(url)
    stored = dict(payload)
    stored.pop("expires_at", None)
    _STORE.set(key, stored, ttl_s=effective_ttl)


def clear_url_citation_page_cache() -> None:
    _STORE.clear()
