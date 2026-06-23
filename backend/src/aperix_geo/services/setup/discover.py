"""Setup discover：微观利基画像 + 竞品发现（不含监测主题）。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from aperix_geo.utils.net import registrable_from
from aperix_geo.services.competitor.profile import keywords_list, profile_from_dict, profile_to_dict
from aperix_geo.services.setup.cache import (
    create_session,
    get_profile_cache,
    get_session,
    profile_hash,
    set_profile_cache,
    update_session,
)
from aperix_geo.services.setup.competitors import discover_competitors_for_session
from aperix_geo.services.setup.helpers import require_deepseek_api_key
from aperix_geo.services.setup.llm.stages import run_niche_profile_stage

logger = logging.getLogger(__name__)


def _competitors_for_response(competitors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """API 响应仅含 Step1 UI 字段；完整数据在 session.competitors。"""
    out: list[dict[str, str]] = []
    for item in competitors:
        out.append(
            {
                "domain": str(item.get("domain") or "").strip(),
                "website_url": str(item.get("website_url") or "").strip(),
                "brand": str(item.get("brand") or "").strip(),
            }
        )
    return out


def _resolve_target(
    *,
    subject_type: str,
    domain: str | None,
    brand: str | None,
) -> tuple[str, str]:
    if subject_type == "domain":
        if not domain:
            raise ValueError("domain is required for domain subject type")
        raw_website = domain.strip()
        target = registrable_from(raw_website)
        if not target:
            raise ValueError("invalid domain")
        return target, raw_website
    if not brand or not brand.strip():
        raise ValueError("brand is required for brand subject type")
    return brand.strip(), ""


def _session_matches_request(
    session: dict[str, Any],
    *,
    profile_hash: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
) -> bool:
    return (
        session.get("profile_hash") == profile_hash
        and session.get("subject_type") == subject_type
        and session.get("target") == target
        and session.get("region", "CN") == region
        and session.get("language", "zh-CN") == language
    )


def _load_or_build_profile(
    *,
    user_id: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str,
    profile_hash: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str], bool]:
    cached_profile = get_profile_cache(user_id=user_id, profile_hash=profile_hash)
    if cached_profile is not None:
        profile_dict = cached_profile["profile"]
        research_payload = dict(cached_profile["research_payload"])
        keywords = keywords_list(profile_from_dict(profile_dict)) or ([target] if target else [])
        return profile_dict, research_payload, keywords, True

    profile, research_payload = run_niche_profile_stage(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
    )
    profile_dict = profile_to_dict(profile)
    set_profile_cache(
        user_id=user_id,
        profile_hash=profile_hash,
        profile=profile_dict,
        research_payload=research_payload,
    )
    keywords = keywords_list(profile) or ([target] if target else [])
    return profile_dict, research_payload, keywords, False


def discover_setup(
    *,
    user_id: UUID,
    subject_type: str,
    domain: str | None,
    brand: str | None,
    region: str,
    language: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """建立微观画像并完成竞品发现；可选 session_id 用于退回后缓存命中。"""
    require_deepseek_api_key()

    target, raw_website = _resolve_target(
        subject_type=subject_type,
        domain=domain,
        brand=brand,
    )
    website_url = raw_website if subject_type == "domain" else ""
    profile_hash_value = profile_hash(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
    )

    user_key = str(user_id)
    existing: dict[str, Any] | None = None
    sid = (session_id or "").strip()
    if sid:
        loaded = get_session(user_id=user_key, session_id=sid)
        if loaded and _session_matches_request(
            loaded,
            profile_hash=profile_hash_value,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
        ):
            existing = loaded

    t0 = time.perf_counter()
    if existing is not None:
        session_id = sid
        profile_dict = dict(existing.get("profile") or {})
        keywords = list(existing.get("keywords") or [])
        if not existing.get("research_payload"):
            cached_profile = get_profile_cache(user_id=user_key, profile_hash=profile_hash_value)
            if cached_profile and cached_profile.get("research_payload"):
                update_session(
                    user_id=user_key,
                    session_id=session_id,
                    patch={"research_payload": dict(cached_profile["research_payload"])},
                )
        logger.info(
            "设置向导·发现 复用会话 session=%s target=%r",
            session_id[:8],
            target,
        )
    else:
        profile_dict, research_payload, keywords, from_cache = _load_or_build_profile(
            user_id=user_key,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            website_url=website_url,
            profile_hash=profile_hash_value,
        )
        session_id = create_session(
            user_id=user_key,
            payload={
                "subject_type": subject_type,
                "target": target,
                "domain": target if subject_type == "domain" else None,
                "website_url": raw_website if subject_type == "domain" else None,
                "brand": target if subject_type == "brand" else None,
                "region": region,
                "language": language,
                "profile_hash": profile_hash_value,
                "profile": profile_dict,
                "keywords": keywords,
                "monitoring_topics": [],
                "research_payload": research_payload,
                "profile_summary": "",
            },
        )
        logger.info(
            "设置向导·发现 新建会话 session=%s target=%r type=%s 画像缓存=%s",
            session_id[:8],
            target,
            subject_type,
            from_cache,
        )

    competitors = discover_competitors_for_session(
        user_id=user_id,
        session_id=session_id,
        profile_dict=profile_dict,
        keywords=keywords,
    )

    logger.info(
        "设置向导·发现 完成 session=%s 耗时=%.1fs 竞品=%d",
        session_id[:8],
        time.perf_counter() - t0,
        len(competitors),
    )
    return {
        "session_id": session_id,
        "competitors": _competitors_for_response(competitors),
    }
