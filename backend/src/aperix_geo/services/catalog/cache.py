"""Redis + L1 cache for subject catalog endpoints (entities, topics)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.cache import TieredJsonCache

_ENTITIES_CACHE = TieredJsonCache(
    redis_prefix="aperix:catalog:entities:v1:",
    l1_max_entries=256,
    strip_expires_on_read=True,
)
_TOPICS_CACHE = TieredJsonCache(
    redis_prefix="aperix:catalog:topics:v1:",
    l1_max_entries=256,
    strip_expires_on_read=True,
)

__all__ = [
    "entities_cache_get",
    "entities_cache_set",
    "clear_analysis_entities_cache",
    "clear_subject_catalog_cache",
    "clear_subject_topics_cache",
    "topics_cache_get",
    "topics_cache_set",
]


def _catalog_cache_ttl_s() -> int:
    return get_settings().catalog_cache_ttl_s


def entities_cache_get(subject_id: UUID) -> dict[str, Any] | None:
    ttl_s = _catalog_cache_ttl_s()
    if ttl_s <= 0:
        return None
    payload = _ENTITIES_CACHE.get(str(subject_id), default_ttl_s=ttl_s)
    if not isinstance(payload, dict) or "entities" not in payload:
        return None
    return payload


def entities_cache_set(subject_id: UUID, payload: dict[str, Any]) -> None:
    ttl_s = _catalog_cache_ttl_s()
    if ttl_s <= 0:
        return
    _ENTITIES_CACHE.set(str(subject_id), payload, ttl_s=ttl_s)


def topics_cache_get(subject_id: UUID) -> dict[str, Any] | None:
    ttl_s = _catalog_cache_ttl_s()
    if ttl_s <= 0:
        return None
    payload = _TOPICS_CACHE.get(str(subject_id), default_ttl_s=ttl_s)
    if not isinstance(payload, dict) or "topics" not in payload:
        return None
    return payload


def topics_cache_set(subject_id: UUID, payload: dict[str, Any]) -> None:
    ttl_s = _catalog_cache_ttl_s()
    if ttl_s <= 0:
        return
    _TOPICS_CACHE.set(str(subject_id), payload, ttl_s=ttl_s)


def clear_analysis_entities_cache(subject_id: UUID) -> None:
    _ENTITIES_CACHE.delete(str(subject_id))


def clear_subject_topics_cache(subject_id: UUID) -> None:
    _TOPICS_CACHE.delete(str(subject_id))


def clear_subject_catalog_cache(subject_id: UUID) -> None:
    clear_analysis_entities_cache(subject_id)
    clear_subject_topics_cache(subject_id)
