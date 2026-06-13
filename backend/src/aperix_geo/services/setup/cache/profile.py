"""Setup Step1 画像结果缓存（相同 target/region 跳过重跑 crawl + LLM）。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.setup.cache.session import session_ttl_s
from aperix_geo.utils.cache.redis_kv import shared_redis_client

PROFILE_CACHE_PREFIX = "setup:profile:"


def profile_fingerprint(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
) -> str:
    payload = {
        "subject_type": subject_type,
        "target": target.strip(),
        "region": region.strip(),
        "language": language.strip(),
        "website_url": website_url.strip(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_key(*, user_id: str, fingerprint: str) -> str:
    return f"{PROFILE_CACHE_PREFIX}{user_id}:{fingerprint}"


def get_profile_cache(*, user_id: str, fingerprint: str) -> dict[str, Any] | None:
    client = shared_redis_client()
    if client is None:
        return None
    raw = client.get(_cache_key(user_id=user_id, fingerprint=fingerprint))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    profile = data.get("profile")
    topics = data.get("monitoring_topics")
    research = data.get("research_payload")
    if not isinstance(profile, dict) or not isinstance(topics, list) or not isinstance(research, dict):
        return None
    return data


def set_profile_cache(
    *,
    user_id: str,
    fingerprint: str,
    profile: dict[str, Any],
    monitoring_topics: list[str],
    research_payload: dict[str, Any],
) -> None:
    settings = get_settings()
    client = shared_redis_client()
    if client is None:
        return
    key = _cache_key(user_id=user_id, fingerprint=fingerprint)
    payload = json.dumps(
        {
            "profile": profile,
            "monitoring_topics": monitoring_topics,
            "research_payload": research_payload,
        },
        ensure_ascii=False,
    )
    ttl_s = session_ttl_s(settings)
    if ttl_s > 0:
        client.setex(key, ttl_s, payload)
    else:
        client.set(key, payload)
