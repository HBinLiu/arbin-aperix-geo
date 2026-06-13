"""Setup 向导 Redis 会话（分步 discover API 共享参数）。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from aperix_geo.config import Settings, get_settings
from aperix_geo.utils.cache.redis_kv import require_redis_client

SESSION_PREFIX = "setup:discovery:"


def _key(user_id: str, session_id: str) -> str:
    return f"{SESSION_PREFIX}{user_id}:{session_id}"


def session_ttl_s(settings: Settings | None = None) -> int:
    return (settings or get_settings()).setup_session_ttl_s


def _save_session(*, user_id: str, session_id: str, data: dict[str, Any]) -> None:
    settings = get_settings()
    client = require_redis_client()
    payload = json.dumps(data, ensure_ascii=False)
    key = _key(user_id, session_id)
    ttl_s = session_ttl_s(settings)
    if ttl_s > 0:
        client.setex(key, ttl_s, payload)
    else:
        client.set(key, payload)


def create_session(*, user_id: str, payload: dict[str, Any]) -> str:
    """创建设置向导会话（默认 24h TTL；finalize 成功后显式删除）。"""
    session_id = uuid.uuid4().hex
    data = dict(payload)
    data["user_id"] = user_id
    _save_session(user_id=user_id, session_id=session_id, data=data)
    return session_id


def get_session(*, user_id: str, session_id: str) -> dict[str, Any] | None:
    client = require_redis_client()
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


def update_session(*, user_id: str, session_id: str, patch: dict[str, Any]) -> bool:
    current = get_session(user_id=user_id, session_id=session_id)
    if current is None:
        return False
    for key, value in patch.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = value
    _save_session(user_id=user_id, session_id=session_id, data=current)
    return True


def delete_session(*, user_id: str, session_id: str) -> bool:
    """Setup 落库成功后删除会话。"""
    deleted = require_redis_client().delete(_key(user_id, session_id))
    return bool(deleted)
