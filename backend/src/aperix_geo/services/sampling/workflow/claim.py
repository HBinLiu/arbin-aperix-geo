"""Redis claim lock so sampling workers release DB row locks during LLM/parse."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.utils.cache.redis_kv import redis_delete, redis_set_nx

_CLAIM_PREFIX = "aperix:sampling:response_claim:"
_CLAIM_TTL_S = 900


def try_claim_response(response_id: UUID) -> bool:
    """Return True when this worker may process the pending response."""
    return redis_set_nx(f"{_CLAIM_PREFIX}{response_id}", ttl_s=_CLAIM_TTL_S)


def release_response_claim(response_id: UUID) -> None:
    redis_delete(f"{_CLAIM_PREFIX}{response_id}")
