"""Setup Step3 提示词生成 session 缓存。"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.prompts.context import entity_aliases
from aperix_geo.services.prompts.setup import PROMPTS_PER_TOPIC, generate_setup_prompts
from aperix_geo.services.setup.cache.session import get_session, update_session

logger = logging.getLogger(__name__)


def prompts_generation_fingerprint(
    *,
    entity: str,
    topics: list[str],
    competitors: list[str],
    industry: str,
    core_features: str,
    target_customers: str,
    aliases: list[str],
    exclude_prompts: list[str],
    prompts_per_topic: int = PROMPTS_PER_TOPIC,
) -> str:
    payload = {
        "entity": entity.strip(),
        "topics": sorted(t.strip() for t in topics if t.strip()),
        "competitors": sorted(c.strip() for c in competitors if c.strip()),
        "industry": industry.strip(),
        "core_features": core_features.strip(),
        "target_customers": target_customers.strip(),
        "aliases": sorted(a.strip() for a in aliases if a.strip()),
        "exclude_prompts": sorted(p.strip() for p in exclude_prompts if p.strip())[-60:],
        "prompts_per_topic": prompts_per_topic,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cached_prompts(session: dict[str, Any], *, fingerprint: str) -> list[dict[str, Any]] | None:
    if session.get("prompts_fingerprint") != fingerprint:
        return None
    cached = session.get("prompts_cache")
    if not isinstance(cached, list) or not cached:
        return None
    return cached


def generate_setup_prompts_for_session(
    *,
    user_id: str,
    session_id: str,
    topics: list[str],
    competitors: list[str],
    exclude_prompts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """按 session 生成初始提示词；相同输入命中 Redis 缓存，跳过重跑 LLM。"""
    session = get_session(user_id=user_id, session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    entity = str(session.get("target") or "").strip()
    if not entity:
        raise ValueError("setup session missing target")

    profile = profile_from_dict(session.get("profile") or {})
    aliases = entity_aliases(
        entity=entity,
        profile_company=str(profile.get("company") or ""),
    )
    excluded = exclude_prompts or []
    fingerprint = prompts_generation_fingerprint(
        entity=entity,
        topics=topics,
        competitors=competitors,
        industry=str(profile.get("industry") or ""),
        core_features=str(profile.get("core_features") or ""),
        target_customers=str(profile.get("target_customers") or ""),
        aliases=aliases,
        exclude_prompts=excluded,
    )

    cached = cached_prompts(session, fingerprint=fingerprint)
    if cached is not None:
        logger.info(
            "设置向导: 提示词缓存命中 session=%s topics=%d",
            session_id[:8],
            len(cached),
        )
        return cached

    items = generate_setup_prompts(
        entity=entity,
        topics=topics,
        industry=str(profile.get("industry") or ""),
        core_features=str(profile.get("core_features") or ""),
        target_customers=str(profile.get("target_customers") or ""),
        competitors=competitors,
        aliases=aliases,
        exclude_prompts=excluded,
    )
    update_session(
        user_id=user_id,
        session_id=session_id,
        patch={
            "prompts_fingerprint": fingerprint,
            "prompts_cache": items,
        },
    )
    return items
