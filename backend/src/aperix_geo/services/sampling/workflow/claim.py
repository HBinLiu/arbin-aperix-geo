"""Redis claim lock so sampling workers release DB row locks during LLM/parse."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.cache.redis_kv import redis_delete, redis_expire, redis_set_nx_strict

_CLAIM_PREFIX = "aperix:sampling:response_claim:"


def _claim_key(response_id: UUID) -> str:
    return f"{_CLAIM_PREFIX}{response_id}"


def _claim_ttl_s() -> int:
    return get_settings().sampling_response_claim_ttl_s


def try_claim_response(response_id: UUID) -> bool:
    """Return True when this worker may process the pending response."""
    return redis_set_nx_strict(_claim_key(response_id), ttl_s=_claim_ttl_s())


def refresh_response_claim(response_id: UUID) -> None:
    """Extend claim TTL after slow LLM/parse work completes."""
    redis_expire(_claim_key(response_id), ttl_s=_claim_ttl_s())


def release_response_claim(response_id: UUID) -> None:
    redis_delete(_claim_key(response_id))
