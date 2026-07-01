"""Setup UI Step 0→1 discover：画像跨 session 缓存。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.setup.cache.session import session_ttl_s
from aperix_geo.utils.cache.redis_kv import shared_redis_client

PROFILE_CACHE_PREFIX = "setup:profile:"


def profile_hash(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
    materials_fingerprint: str = "",
) -> str:
    payload = {
        "subject_type": subject_type,
        "target": target.strip(),
        "region": region.strip(),
        "language": language.strip(),
        "website_url": website_url.strip(),
        "materials_fingerprint": materials_fingerprint.strip(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_key(*, user_id: str, profile_hash: str) -> str:
    return f"{PROFILE_CACHE_PREFIX}{user_id}:{profile_hash}"


def get_profile_cache(*, user_id: str, profile_hash: str) -> dict[str, Any] | None:
    client = shared_redis_client()
    if client is None:
        return None
    raw = client.get(_cache_key(user_id=user_id, profile_hash=profile_hash))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    profile = data.get("profile")
    research = data.get("research_payload")
    if not isinstance(profile, dict) or not isinstance(research, dict):
        return None
    return data


def set_profile_cache(
    *,
    user_id: str,
    profile_hash: str,
    profile: dict[str, Any],
    research_payload: dict[str, Any],
) -> None:
    settings = get_settings()
    client = shared_redis_client()
    if client is None:
        return
    key = _cache_key(user_id=user_id, profile_hash=profile_hash)
    payload = json.dumps(
        {
            "profile": profile,
            "research_payload": research_payload,
        },
        ensure_ascii=False,
    )
    ttl_s = session_ttl_s(settings)
    if ttl_s > 0:
        client.setex(key, ttl_s, payload)
    else:
        client.set(key, payload)
