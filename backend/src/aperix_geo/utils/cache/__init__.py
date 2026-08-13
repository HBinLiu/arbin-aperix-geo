"""Shared cache utilities (bounded memory, Redis TTL, single-flight).

Redis helpers are lazy so geo-web-crawl / DNS callers that only need
``BoundedTTLCache`` do not require the ``redis`` package at import time.
"""

from __future__ import annotations

from typing import Any

from aperix_geo.utils.cache.bounded import BoundedTTLCache
from aperix_geo.utils.cache.ttl import expires_at_from_ttl, is_payload_expired, remaining_ttl_s

__all__ = [
    "BoundedTTLCache",
    "clear_redis_kv_cache",
    "expires_at_from_ttl",
    "is_payload_expired",
    "redis_delete",
    "redis_get_json",
    "redis_get_json_with_remaining_ttl",
    "redis_set_json_exat",
    "redis_set_json_persistent",
    "redis_set_nx",
    "redis_set_nx_strict",
    "require_redis_client",
    "shared_redis_client",
    "remaining_ttl_s",
    "run_single_flight",
    "SingleFlightWaitTimeout",
    "TieredJsonCache",
]


def __getattr__(name: str) -> Any:
    if name in {
        "clear_redis_kv_cache",
        "redis_delete",
        "redis_get_json",
        "redis_get_json_with_remaining_ttl",
        "redis_set_json_exat",
        "redis_set_json_persistent",
        "redis_set_nx",
        "redis_set_nx_strict",
        "require_redis_client",
        "shared_redis_client",
    }:
        from aperix_geo.utils.cache import redis_kv

        return getattr(redis_kv, name)
    if name in {"SingleFlightWaitTimeout", "run_single_flight"}:
        from aperix_geo.utils.cache import coalesce

        return getattr(coalesce, name)
    if name == "TieredJsonCache":
        from aperix_geo.utils.cache.tiered_json import TieredJsonCache

        return TieredJsonCache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
