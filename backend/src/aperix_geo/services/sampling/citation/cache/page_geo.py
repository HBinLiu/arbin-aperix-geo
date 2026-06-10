"""Cache for per-URL page GEO LLM results (global, url+snippet-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.utils.cache import TieredJsonCache
from aperix_geo.utils.url import normalize_crawl_cache_url

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:page_geo:v1:",
    l1_max_entries=256,
    strip_expires_on_read=True,
)


def _cache_key(
    *,
    url: str,
    text_snippet: str,
    own_brand: str,
    competitors: list[str],
) -> str:
    normalized_url = normalize_crawl_cache_url(url)
    comp = ",".join(sorted(c.strip() for c in competitors if c.strip()))
    raw = f"{normalized_url}|{text_snippet[:2000]}|{own_brand.strip()}|{comp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def page_geo_cache_digest(
    *,
    url: str,
    text_snippet: str,
    own_brand: str,
    competitors: list[str],
) -> str:
    return _cache_key(
        url=url,
        text_snippet=text_snippet,
        own_brand=own_brand,
        competitors=competitors,
    )


def _is_valid(payload: dict[str, Any]) -> bool:
    return bool(payload.get("analysis_source"))


def get_page_geo_cached(
    *,
    url: str,
    text_snippet: str,
    own_brand: str,
    competitors: list[str],
    ttl_s: int,
) -> dict[str, Any] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(
        url=url,
        text_snippet=text_snippet,
        own_brand=own_brand,
        competitors=competitors,
    )
    return _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)


def set_page_geo_cached(
    *,
    url: str,
    text_snippet: str,
    own_brand: str,
    competitors: list[str],
    result: dict[str, Any],
    ttl_s: int,
) -> None:
    key = _cache_key(
        url=url,
        text_snippet=text_snippet,
        own_brand=own_brand,
        competitors=competitors,
    )
    payload = dict(result)
    payload.pop("expires_at", None)
    _STORE.set(
        key,
        payload,
        ttl_s=ttl_s,
        skip_if=lambda data: data.get("analysis_source") == "failed",
    )
    if ttl_s > 0 and result.get("analysis_source") != "failed":
        logger.debug("Page GEO 缓存写入 %s", normalize_crawl_cache_url(url.strip()))


def clear_page_geo_cache() -> None:
    _STORE.clear()
