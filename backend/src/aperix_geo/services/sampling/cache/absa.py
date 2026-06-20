"""Cache for whole-response ABSA LLM results (global, content-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.services.providers.prompts import citation_response_absa_system
from aperix_geo.utils.cache import TieredJsonCache

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:response_absa:v4:",
    l1_max_entries=128,
    strip_expires_on_read=True,
)


def response_absa_prompt_digest(*, open_set_enabled: bool = True) -> str:
    system = citation_response_absa_system(open_set_enabled=open_set_enabled)
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:12]


def _scope_digest(
    *,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None,
    open_set_enabled: bool,
) -> str:
    comp = ",".join(sorted(c.strip() for c in competitors if c.strip()))
    excluded = ",".join(sorted(excluded_keys or []))
    prompt = response_absa_prompt_digest(open_set_enabled=open_set_enabled)
    open_flag = "open" if open_set_enabled else "closed"
    raw = f"{prompt}|{open_flag}|{own_brand.strip()}|{comp}|{excluded}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _cache_key(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    open_set_enabled: bool = True,
) -> str:
    digest = hashlib.sha256(raw_text[:8000].encode("utf-8")).hexdigest()[:32]
    scope = _scope_digest(
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        open_set_enabled=open_set_enabled,
    )
    return hashlib.sha256(f"{digest}|{scope}".encode("utf-8")).hexdigest()


def response_absa_cache_digest(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    open_set_enabled: bool = True,
) -> str:
    return _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        open_set_enabled=open_set_enabled,
    )


def _is_valid(payload: dict[str, Any]) -> bool:
    return bool(payload.get("analysis_source"))


def get_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    open_set_enabled: bool = True,
    ttl_s: int,
) -> dict[str, Any] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        open_set_enabled=open_set_enabled,
    )
    return _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)


def set_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    open_set_enabled: bool = True,
    result: dict[str, Any],
    ttl_s: int,
) -> None:
    key = _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        open_set_enabled=open_set_enabled,
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
        logger.debug("Response ABSA 缓存写入 brand=%s", own_brand.strip())


def clear_response_absa_cache() -> None:
    _STORE.clear()
