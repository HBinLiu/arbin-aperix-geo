"""新增品牌/域名设置向导：Redis 会话（分步 discover API 共享参数）。"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis

from aperix_geo.config import Settings, get_settings

SESSION_PREFIX = "setup:discovery:"
DEFAULT_TTL_S = 3600


def _redis(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _key(user_id: str, session_id: str) -> str:
    return f"{SESSION_PREFIX}{user_id}:{session_id}"


def create_session(*, user_id: str, payload: dict[str, Any], ttl_s: int = DEFAULT_TTL_S) -> str:
    session_id = uuid.uuid4().hex
    data = dict(payload)
    data["user_id"] = user_id
    _redis(get_settings()).setex(_key(user_id, session_id), ttl_s, json.dumps(data, ensure_ascii=False))
    return session_id


def get_session(*, user_id: str, session_id: str) -> dict[str, Any] | None:
    client = _redis(get_settings())
    raw = client.get(_key(user_id, session_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def update_session(*, user_id: str, session_id: str, patch: dict[str, Any], ttl_s: int = DEFAULT_TTL_S) -> bool:
    current = get_session(user_id=user_id, session_id=session_id)
    if current is None:
        return False
    current.update(patch)
    _redis(get_settings()).setex(
        _key(user_id, session_id),
        ttl_s,
        json.dumps(current, ensure_ascii=False),
    )
    return True
