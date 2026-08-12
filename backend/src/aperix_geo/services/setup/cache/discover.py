"""Setup discover 异步任务状态（Celery 跑画像；topics 短等）。"""

from __future__ import annotations

import json
import time
from typing import Any, Literal

from aperix_geo.config import get_settings
from aperix_geo.services.setup.cache.session import session_ttl_s
from aperix_geo.utils.cache.redis_kv import require_redis_client

DiscoverJobStatus = Literal["pending", "running", "ready", "failed"]

JOB_PREFIX = "setup:discover_job:"
HASH_INDEX_PREFIX = "setup:discover_job_by_hash:"


def _job_key(*, user_id: str, session_id: str) -> str:
    return f"{JOB_PREFIX}{user_id}:{session_id}"


def _hash_index_key(*, user_id: str, profile_hash: str) -> str:
    return f"{HASH_INDEX_PREFIX}{user_id}:{profile_hash}"


def _ttl_s() -> int:
    return session_ttl_s(get_settings())


def _setex(key: str, payload: str) -> None:
    client = require_redis_client()
    ttl = _ttl_s()
    if ttl > 0:
        client.setex(key, ttl, payload)
    else:
        client.set(key, payload)


def get_discover_job(*, user_id: str, session_id: str) -> dict[str, Any] | None:
    raw = require_redis_client().get(_job_key(user_id=user_id, session_id=session_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def set_discover_job(
    *,
    user_id: str,
    session_id: str,
    status: DiscoverJobStatus,
    profile_hash: str = "",
    error: str = "",
) -> None:
    payload = {
        "status": status,
        "session_id": session_id,
        "profile_hash": profile_hash,
        "error": error,
        "updated_at": int(time.time()),
    }
    _setex(_job_key(user_id=user_id, session_id=session_id), json.dumps(payload, ensure_ascii=False))
    if profile_hash:
        _setex(_hash_index_key(user_id=user_id, profile_hash=profile_hash), session_id)


def find_active_discover_session(*, user_id: str, profile_hash: str) -> str | None:
    """同 profile_hash 若已有 pending/running job，返回其 session_id。"""
    client = require_redis_client()
    sid_raw = client.get(_hash_index_key(user_id=user_id, profile_hash=profile_hash))
    if not sid_raw:
        return None
    session_id = str(sid_raw)
    job = get_discover_job(user_id=user_id, session_id=session_id)
    if not job:
        return None
    if job.get("status") in ("pending", "running"):
        return session_id
    return None


def wait_discover_job(
    *,
    user_id: str,
    session_id: str,
    timeout_s: float = 120.0,
    poll_s: float = 1.0,
) -> dict[str, Any]:
    """阻塞直到 job ready/failed，或超时。返回最终 job dict。"""
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last = get_discover_job(user_id=user_id, session_id=session_id)
        if last is not None:
            status = str(last.get("status") or "")
            if status in ("ready", "failed"):
                return last
        time.sleep(poll_s)
    return last or {"status": "failed", "error": "画像生成超时，请稍后重试", "session_id": session_id}
