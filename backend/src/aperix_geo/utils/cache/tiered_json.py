"""L1 memory + Redis JSON cache with optional TTL-aware Redis reads."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aperix_geo.utils.cache.bounded import BoundedTTLCache
from aperix_geo.utils.cache.redis_kv import redis_get_json, redis_get_json_with_remaining_ttl, redis_set_json_exat
from aperix_geo.utils.cache.ttl import expires_at_from_ttl


@dataclass
class TieredJsonCache:
    """Two-tier JSON payload cache: process-local L1 + shared Redis."""

    redis_prefix: str
    l1_max_entries: int = 128
    strip_expires_on_read: bool = False
    use_remaining_ttl: bool = True

    _l1: BoundedTTLCache = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._l1 = BoundedTTLCache(self.l1_max_entries)

    @staticmethod
    def strip_expires(payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key != "expires_at"}

    def _redis_key(self, key: str) -> str:
        return f"{self.redis_prefix}{key}"

    def _out(self, payload: dict[str, Any]) -> dict[str, Any]:
        copied = dict(payload)
        return self.strip_expires(copied) if self.strip_expires_on_read else copied

    def get(
        self,
        key: str,
        *,
        default_ttl_s: int = 3600,
        is_valid: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any] | None:
        cached = self._l1.get(key)
        if isinstance(cached, dict) and (is_valid is None or is_valid(cached)):
            return self._out(cached)

        redis_key = self._redis_key(key)
        if self.use_remaining_ttl:
            hit = redis_get_json_with_remaining_ttl(redis_key)
            if hit is None:
                return None
            payload, remaining = hit
            if not isinstance(payload, dict) or (is_valid is not None and not is_valid(payload)):
                return None
            expires_at = int(payload.get("expires_at") or (time.time() + remaining))
        else:
            payload = redis_get_json(redis_key)
            if not isinstance(payload, dict) or (is_valid is not None and not is_valid(payload)):
                return None
            expires_at = int(payload.get("expires_at") or (time.time() + default_ttl_s))

        stored = dict(payload)
        self._l1.set(key, stored, expires_at=expires_at)
        return self._out(stored)

    def set(
        self,
        key: str,
        payload: dict[str, Any],
        *,
        ttl_s: int,
        skip_if: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        if ttl_s <= 0:
            return
        data = dict(payload)
        if skip_if is not None and skip_if(data):
            return
        expires_at = expires_at_from_ttl(ttl_s)
        data["expires_at"] = expires_at
        self._l1.set(key, data, expires_at=expires_at)
        redis_set_json_exat(self._redis_key(key), data, expires_at=expires_at)

    def clear(self) -> None:
        self._l1.clear()
