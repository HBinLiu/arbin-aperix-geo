"""Cache for response mention discovery LLM results (global, content-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.services.providers.prompts import CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM
from aperix_geo.utils.cache import TieredJsonCache

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:mention_discovery:v1:",
    l1_max_entries=128,
    strip_expires_on_read=True,
)


def mention_discovery_prompt_digest() -> str:
    system = CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:12]


def _cache_key(*, raw_text: str) -> str:
    prompt = mention_discovery_prompt_digest()
    digest = hashlib.sha256(raw_text[:8000].encode("utf-8")).hexdigest()[:32]
    return hashlib.sha256(f"{prompt}|{digest}".encode("utf-8")).hexdigest()


def mention_discovery_cache_digest(*, raw_text: str) -> str:
    return _cache_key(raw_text=raw_text)


def _is_valid(payload: dict[str, Any]) -> bool:
    return payload.get("analysis_source") == "llm"


def get_mention_discovery_cached(*, raw_text: str, ttl_s: int) -> list[str] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(raw_text=raw_text)
    payload = _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)
    if payload is None:
        return None
    spans = payload.get("mentioned_spans")
    if not isinstance(spans, list):
        return None
    return [str(item).strip() for item in spans if str(item).strip()]


def set_mention_discovery_cached(
    *,
    raw_text: str,
    mentioned_spans: list[str],
    ttl_s: int,
) -> None:
    key = _cache_key(raw_text=raw_text)
    _STORE.set(
        key,
        {
            "analysis_source": "llm",
            "mentioned_spans": mentioned_spans,
        },
        ttl_s=ttl_s,
        skip_if=lambda data: data.get("analysis_source") != "llm",
    )
    if ttl_s > 0:
        logger.debug("Mention discovery 缓存写入 spans=%d", len(mentioned_spans))


def clear_mention_discovery_cache() -> None:
    _STORE.clear()
