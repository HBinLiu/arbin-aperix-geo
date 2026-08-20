"""Cache for response mention discovery LLM results (global, content-keyed)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aperix_geo.services.providers.prompts import CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM
from aperix_geo.utils.cache import TieredJsonCache

logger = logging.getLogger(__name__)

_STORE = TieredJsonCache(
    redis_prefix="aperix:mention_discovery:v2:",
    l1_max_entries=128,
    strip_expires_on_read=True,
)


def mention_discovery_prompt_digest() -> str:
    system = CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:12]


def _track_digest(track_context: str) -> str:
    track = track_context.strip()[:240]
    if not track:
        return ""
    return hashlib.sha256(track.encode("utf-8")).hexdigest()[:12]


def _cache_key(*, raw_text: str, track_context: str = "") -> str:
    prompt = mention_discovery_prompt_digest()
    digest = hashlib.sha256(raw_text[:8000].encode("utf-8")).hexdigest()[:32]
    track = _track_digest(track_context)
    return hashlib.sha256(f"{prompt}|{digest}|{track}".encode("utf-8")).hexdigest()


def mention_discovery_cache_digest(*, raw_text: str, track_context: str = "") -> str:
    return _cache_key(raw_text=raw_text, track_context=track_context)


def _is_valid(payload: dict[str, Any]) -> bool:
    return payload.get("analysis_source") == "llm"


def get_mention_discovery_cached(
    *,
    raw_text: str,
    ttl_s: int,
    track_context: str = "",
) -> list[dict[str, Any]] | None:
    if ttl_s <= 0:
        return None
    key = _cache_key(raw_text=raw_text, track_context=track_context)
    payload = _STORE.get(key, default_ttl_s=ttl_s, is_valid=_is_valid)
    if payload is None:
        return None
    entities = payload.get("entities")
    if isinstance(entities, list):
        return [dict(item) for item in entities if isinstance(item, dict)]
    spans = payload.get("mentioned_spans")
    if isinstance(spans, list):
        return [{"text": str(item).strip()} for item in spans if str(item).strip()]
    return None


def set_mention_discovery_cached(
    *,
    raw_text: str,
    entities: list[dict[str, Any]],
    ttl_s: int,
    track_context: str = "",
) -> None:
    key = _cache_key(raw_text=raw_text, track_context=track_context)
    _STORE.set(
        key,
        {
            "analysis_source": "llm",
            "entities": entities,
        },
        ttl_s=ttl_s,
        skip_if=lambda data: data.get("analysis_source") != "llm",
    )
    if ttl_s > 0:
        logger.debug("Mention discovery 缓存写入 entities=%d", len(entities))


def clear_mention_discovery_cache() -> None:
    _STORE.clear()
