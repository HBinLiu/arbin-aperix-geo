"""Cache for whole-response ABSA LLM results (global, content-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.services.providers.prompts import CITATION_RESPONSE_ABSA_SYSTEM
from aperix_geo.utils.cache import TieredJsonCache

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:response_absa:v5:",
    l1_max_entries=128,
    strip_expires_on_read=True,
)


def response_absa_prompt_digest() -> str:
    system = CITATION_RESPONSE_ABSA_SYSTEM
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:12]


def _candidates_digest(mention_candidates: list[str] | None) -> str:
    if not mention_candidates:
        return ""
    joined = "\n".join(mention_candidates)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _track_digest(track_context: str) -> str:
    track = track_context.strip()[:240]
    if not track:
        return ""
    return hashlib.sha256(track.encode("utf-8")).hexdigest()[:12]


def _scope_digest(
    *,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
) -> str:
    comp = ",".join(sorted(c.strip() for c in competitors if c.strip()))
    excluded = ",".join(sorted(excluded_keys or []))
    prompt = response_absa_prompt_digest()
    candidates = _candidates_digest(mention_candidates)
    track = _track_digest(track_context)
    raw = f"{prompt}|{own_brand.strip()}|{comp}|{excluded}|{candidates}|{track}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _cache_key(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
) -> str:
    digest = hashlib.sha256(raw_text[:8000].encode("utf-8")).hexdigest()[:32]
    scope = _scope_digest(
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        mention_candidates=mention_candidates,
        track_context=track_context,
    )
    return hashlib.sha256(f"{digest}|{scope}".encode("utf-8")).hexdigest()


def response_absa_cache_digest(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
) -> str:
    return _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        mention_candidates=mention_candidates,
        track_context=track_context,
    )


def _is_valid(payload: dict[str, Any]) -> bool:
    return bool(payload.get("analysis_source"))


def get_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
    ttl_s: int,
) -> dict[str, Any] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        mention_candidates=mention_candidates,
        track_context=track_context,
    )
    return _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)


def set_response_absa_cached(
    *,
    raw_text: str,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
    result: dict[str, Any],
    ttl_s: int,
) -> None:
    key = _cache_key(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
        excluded_keys=excluded_keys,
        mention_candidates=mention_candidates,
        track_context=track_context,
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
