"""Best-effort Redis JSON key-value helpers (fail open)."""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Any

import redis

from aperix_geo.config import get_settings
from aperix_geo.utils.cache.ttl import is_payload_expired, remaining_ttl_s

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _redis_client() -> redis.Redis | None:
    try:
        return redis.from_url(get_settings().redis_url, decode_responses=True)
    except Exception:
        logger.debug("Redis 客户端初始化失败", exc_info=True)
        return None


def redis_get_json(key: str) -> dict[str, Any] | None:
    client = _redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if is_payload_expired(data):
            return None
        return data
    except Exception:
        logger.debug("Redis GET 失败 key=%s", key, exc_info=True)
        return None


def redis_get_json_with_remaining_ttl(key: str) -> tuple[dict[str, Any], int] | None:
    """Return (payload, remaining_seconds) using expires_at when present."""
    data = redis_get_json(key)
    if data is None:
        return None
    ttl = remaining_ttl_s(data)
    if ttl <= 0:
        return None
    return data, ttl


def redis_set_json_exat(key: str, value: dict[str, Any], *, expires_at: int) -> None:
    if time.time() >= expires_at:
        return
    client = _redis_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value, ensure_ascii=False), exat=expires_at)
    except Exception:
        logger.debug("Redis SET EXAT 失败 key=%s", key, exc_info=True)


def redis_set_json_persistent(key: str, value: dict[str, Any]) -> None:
    """SET without TTL; omit expires_at so reads never treat the payload as expired."""
    client = _redis_client()
    if client is None:
        return
    payload = {k: v for k, v in value.items() if k != "expires_at"}
    try:
        client.set(key, json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.debug("Redis SET 失败 key=%s", key, exc_info=True)


def redis_set_nx(key: str, *, ttl_s: int, fail_open: bool = True) -> bool:
    """SET NX with TTL. When Redis is unavailable, fail_open=True returns True (legacy)."""
    client = _redis_client()
    if client is None:
        return fail_open
    try:
        return bool(client.set(key, "1", nx=True, ex=max(1, ttl_s)))
    except Exception:
        logger.debug("Redis SET NX 失败 key=%s", key, exc_info=True)
        return fail_open


def redis_set_nx_strict(key: str, *, ttl_s: int) -> bool:
    """SET NX; returns False when Redis is unavailable (sampling locks / debounce)."""
    return redis_set_nx(key, ttl_s=ttl_s, fail_open=False)


def redis_expire(key: str, *, ttl_s: int) -> None:
    client = _redis_client()
    if client is None:
        return
    try:
        client.expire(key, max(1, ttl_s))
    except Exception:
        logger.debug("Redis EXPIRE 失败 key=%s", key, exc_info=True)


def redis_delete(key: str) -> None:
    client = _redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        logger.debug("Redis DEL 失败 key=%s", key, exc_info=True)


def redis_incr(key: str, *, ttl_s: int) -> int | None:
    """INCR with TTL refresh. Returns new value or None when Redis unavailable."""
    client = _redis_client()
    if client is None:
        return None
    try:
        value = int(client.incr(key))
        client.expire(key, max(1, ttl_s))
        return value
    except Exception:
        logger.debug("Redis INCR 失败 key=%s", key, exc_info=True)
        return None


def redis_decr(key: str, *, ttl_s: int) -> int | None:
    """DECR with TTL refresh. Clamps negative values back to zero."""
    client = _redis_client()
    if client is None:
        return None
    try:
        value = int(client.decr(key))
        if value < 0:
            client.set(key, "0", ex=max(1, ttl_s))
            return 0
        client.expire(key, max(1, ttl_s))
        return value
    except Exception:
        logger.debug("Redis DECR 失败 key=%s", key, exc_info=True)
        return None


def shared_redis_client() -> redis.Redis | None:
    """Process-wide Redis client (decode_responses=True)."""
    return _redis_client()


def require_redis_client() -> redis.Redis:
    """Shared Redis client; raises when Redis is unavailable."""
    client = _redis_client()
    if client is None:
        raise RuntimeError("Redis 不可用")
    return client


def clear_redis_kv_cache() -> None:
    _redis_client.cache_clear()
