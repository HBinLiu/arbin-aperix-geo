"""Shared cache utilities (bounded memory, Redis TTL, single-flight)."""

from aperix_geo.utils.cache.bounded import BoundedTTLCache
from aperix_geo.utils.cache.coalesce import run_single_flight
from aperix_geo.utils.cache.redis_kv import (
    clear_redis_kv_cache,
    redis_delete,
    redis_get_json,
    redis_get_json_with_remaining_ttl,
    redis_set_json,
    redis_set_json_exat,
    redis_set_nx,
)
from aperix_geo.utils.cache.ttl import expires_at_from_ttl, is_payload_expired, remaining_ttl_s

__all__ = [
    "BoundedTTLCache",
    "clear_redis_kv_cache",
    "expires_at_from_ttl",
    "is_payload_expired",
    "redis_delete",
    "redis_get_json",
    "redis_get_json_with_remaining_ttl",
    "redis_set_json",
    "redis_set_json_exat",
    "redis_set_nx",
    "remaining_ttl_s",
    "run_single_flight",
]
