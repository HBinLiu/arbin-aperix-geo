"""Cache for whole-response ABSA LLM results (global, content-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.utils.cache import TieredJsonCache

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:response_absa:v1:",
    l1_max_entries=128,
    strip_expires_on_read=True,
)


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


def _is_valid(payload: dict[str, Any]) -> bool:
    return bool(payload.get("analysis_source"))


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
    return _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)


def set_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    result: dict[str, Any],
    ttl_s: int,
) -> None:
    key = _cache_key(raw_text=raw_text, own_brand=own_brand, competitors=competitors)
    payload = dict(result)
    payload.pop("expires_at", None)
    _STORE.set(
        key,
        payload,
        ttl_s=ttl_s,
        skip_if=lambda data: data.get("analysis_source") == "failed",
    )
    if ttl_s > 0 and result.get("analysis_source") != "failed":
        logger.debug("Response ABSA 缓存写入 brand=%s", own_brand.strip())


def clear_response_absa_cache() -> None:
    _STORE.clear()
