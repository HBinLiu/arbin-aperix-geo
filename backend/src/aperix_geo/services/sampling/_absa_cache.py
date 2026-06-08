"""TTL cache for response ABSA LLM results (L1 memory + L2 Redis)."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from aperix_geo.utils.cache import (
    BoundedTTLCache,
    expires_at_from_ttl,
    redis_get_json_with_remaining_ttl,
    redis_set_json_exat,
)

logger = logging.getLogger(__name__)

_L1_MAX_ENTRIES = 128
_memory = BoundedTTLCache(_L1_MAX_ENTRIES)
_REDIS_PREFIX = "aperix:response_absa:v1:"


def _cache_key(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
) -> str:
    comp = ",".join(sorted(c.strip() for c in competitors if c.strip()))
    digest = hashlib.sha256(raw_text[:8000].encode("utf-8")).hexdigest()[:32]
    raw = f"{digest}|{own_brand.strip()}|{comp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def response_absa_cache_digest(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
) -> str:
    return _cache_key(raw_text=raw_text, own_brand=own_brand, competitors=competitors)


def _strip_expires(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "expires_at"}


def get_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    ttl_s: int,
) -> dict[str, Any] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(raw_text=raw_text, own_brand=own_brand, competitors=competitors)
    payload = _memory.get(key)
    if payload is not None and payload.get("analysis_source"):
        return _strip_expires(dict(payload))
    hit = redis_get_json_with_remaining_ttl(f"{_REDIS_PREFIX}{key}")
    if hit is None:
        return None
    data, remaining = hit
    if not data.get("analysis_source"):
        return None
    now = time.time()
    expires_at = int(data.get("expires_at") or (now + remaining))
    _memory.set(key, dict(data), expires_at=expires_at)
    return _strip_expires(data)


def set_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    result: dict[str, Any],
    ttl_s: int,
) -> None:
    if ttl_s <= 0 or result.get("analysis_source") == "failed":
        return
    key = _cache_key(raw_text=raw_text, own_brank=own_brand, competitors=competitors)
    expires_at = expires_at_from_ttl(ttl_s)
    payload = dict(result)
    payload["expires_at"] = expires_at
    _memory.set(key, payload, expires_at=expires_at)
    redis_set_json_exat(f"{_REDIS_PREFIX}{key}", payload, expires_at=expires_at)
    logger.debug("Response ABSA 缓存写入 brand=%s", own_brand.strip())


def clear_response_absa_cache() -> None:
    _memory.clear()
