"""Cache for fetched citation page metadata (job-scoped URL dedup)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.cache import TieredJsonCache
from aperix_geo.utils.url import normalize_crawl_cache_url

_STORE = TieredJsonCache(
    redis_prefix="aperix:sampling:job_page:v1:",
    l1_max_entries=1024,
    use_remaining_ttl=False,
)


def _job_page_cache_ttl_s() -> int:
    """Align job-scoped citation page cache with global page crawl TTL."""
    return get_settings().page_crawl_cache_ttl_s


def _cache_key(job_id: UUID, url: str) -> str:
    return f"{job_id}:{normalize_crawl_cache_url(url)}"


def get_job_citation_page(job_id: UUID | None, url: str) -> dict[str, Any] | None:
    if job_id is None or not url.strip():
        return None
    ttl_s = _job_page_cache_ttl_s()
    if ttl_s <= 0:
        return None
    return _STORE.get(
        _cache_key(job_id, url),
        default_ttl_s=ttl_s,
        is_valid=lambda payload: bool(payload.get("url")),
    )


def set_job_citation_page(
    job_id: UUID | None,
    payload: dict[str, Any],
    *,
    ttl_s: int | None = None,
) -> None:
    if job_id is None or not str(payload.get("url") or "").strip():
        return
    effective_ttl = _job_page_cache_ttl_s() if ttl_s is None else ttl_s
    if effective_ttl <= 0:
        return
    key = _cache_key(job_id, str(payload["url"]))
    stored = dict(payload)
    stored.pop("expires_at", None)
    _STORE.set(key, stored, ttl_s=effective_ttl)


def clear_job_citation_page_cache() -> None:
    _STORE.clear()
