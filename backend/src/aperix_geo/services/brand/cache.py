"""Persistent Redis + L1 cache for resolved brand primary domains (subject-scoped)."""

from __future__ import annotations

import hashlib
import logging
from uuid import UUID

from aperix_geo.db.models import Brand
from aperix_geo.utils.cache.bounded import BoundedTTLCache
from aperix_geo.utils.cache.redis_kv import redis_get_json, redis_set_json_persistent
from aperix_geo.utils.net import brand_from

logger = logging.getLogger(__name__)

_REDIS_PREFIX = "aperix:brand:domain:v2:"
_L1_PERMANENT_EXPIRES_AT = 2_000_000_000
_L1 = BoundedTTLCache(512)

__all__ = [
    "clear_brand_domain_cache",
    "get_brand_domain_cached",
    "remember_brand_domain_cached",
    "remember_brand_row_domains",
]


def _normalize_brand_key(name: str) -> str:
    return (name or "").strip().casefold()


def _cache_key(subject_id: UUID, brand: str) -> str:
    normalized = _normalize_brand_key(brand)
    digest = hashlib.sha256(f"{subject_id}:{normalized}".encode("utf-8")).hexdigest()
    return digest


def _redis_key(subject_id: UUID, brand: str) -> str:
    return f"{_REDIS_PREFIX}{subject_id}:{_cache_key(subject_id, brand)}"


def get_brand_domain_cached(*, subject_id: UUID, brand: str) -> str | None:
    """Return cached domain or None on miss. Empty string is never cached."""
    name = (brand or "").strip()
    if not name:
        return None

    l1_key = _redis_key(subject_id, name)
    hit = _L1.get(l1_key)
    if isinstance(hit, str) and hit:
        return hit

    payload = redis_get_json(l1_key)
    if not isinstance(payload, dict):
        return None
    domain = brand_from(str(payload.get("domain") or ""))
    if not domain:
        return None
    _L1.set(l1_key, domain, expires_at=_L1_PERMANENT_EXPIRES_AT)
    return domain


def remember_brand_domain_cached(*, subject_id: UUID, brand: str, domain: str) -> None:
    """Persist a resolved domain under brand name (no TTL)."""
    name = (brand or "").strip()
    normalized = brand_from(domain)
    if not name or not normalized:
        return

    l1_key = _redis_key(subject_id, name)
    _L1.set(l1_key, normalized, expires_at=_L1_PERMANENT_EXPIRES_AT)
    redis_set_json_persistent(l1_key, {"domain": normalized})
    logger.debug("品牌域名缓存写入 subject=%s brand=%r domain=%s", subject_id, name, normalized)


def remember_brand_row_domains(*, subject_id: UUID, brand: Brand) -> None:
    """Warm cache for canonical brand name and all aliases."""
    domain = brand_from(brand.domain)
    if not domain:
        return
    remember_brand_domain_cached(subject_id=subject_id, brand=brand.brand, domain=domain)
    for alias in brand.aliases or []:
        text = str(alias or "").strip()
        if text:
            remember_brand_domain_cached(subject_id=subject_id, brand=text, domain=domain)


def clear_brand_domain_cache() -> None:
    _L1.clear()
