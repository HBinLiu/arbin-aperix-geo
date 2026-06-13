"""设置向导：微观利基画像 → 竞品搜索（分步 API）。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.pipeline import search_brand_competitors, search_domain_competitors
from aperix_geo.services.competitor.profile import (
    merge_profile_updates,
    micro_keywords_list,
    profile_from_dict,
    profile_to_dict,
)
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.setup.cache import (
    cached_competitors_result,
    competitors_search_fingerprint,
    create_session,
    get_profile_cache,
    get_session,
    profile_fingerprint,
    session_patch_after_competitors,
    set_profile_cache,
    update_session,
)
from aperix_geo.services.setup.llm.stages import build_subject_profile, run_profile_summary_stage

logger = logging.getLogger(__name__)


def _require_llm_key() -> None:
    if not get_settings().deepseek_api_key.strip():
        raise LLMProviderError("DEEPSEEK_API_KEY is not configured")


def discover_profile(
    *,
    user_id: UUID,
    subject_type: str,
    domain: str | None,
    brand: str | None,
    region: str,
    language: str,
) -> dict[str, Any]:
    """Step 1：生成微观利基画像 + 监测主题，写入 Redis 会话。"""
    _require_llm_key()

    if subject_type == "domain":
        if not domain:
            raise ValueError("domain is required for domain subject type")
        raw_website = domain.strip()
        target = registrable_domain(raw_website)
    else:
        if not brand or not brand.strip():
            raise ValueError("brand is required for brand subject type")
        target = brand.strip()
        raw_website = ""

    website_for_fp = raw_website if subject_type == "domain" else ""
    fp = profile_fingerprint(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_for_fp,
    )
    cached_profile = get_profile_cache(user_id=str(user_id), fingerprint=fp)
    from_cache = cached_profile is not None
    if from_cache:
        profile_dict = cached_profile["profile"]
        profile = profile_from_dict(profile_dict)
        monitoring_topics = list(cached_profile["monitoring_topics"])
        research_payload = dict(cached_profile["research_payload"])
    else:
        profile, monitoring_topics, research_payload = build_subject_profile(
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            website_url=website_for_fp,
        )
        profile_dict = profile_to_dict(profile)
        set_profile_cache(
            user_id=str(user_id),
            fingerprint=fp,
            profile=profile_dict,
            monitoring_topics=monitoring_topics,
            research_payload=research_payload,
        )

    keywords = micro_keywords_list(profile) or ([target] if target else [])

    session_id = create_session(
        user_id=str(user_id),
        payload={
            "subject_type": subject_type,
            "target": target,
            "domain": target if subject_type == "domain" else None,
            "website_url": raw_website if subject_type == "domain" else None,
            "brand": target if subject_type == "brand" else None,
            "region": region,
            "language": language,
            "profile": profile_dict,
            "micro_keywords": keywords,
            "monitoring_topics": monitoring_topics,
            "research_payload": research_payload,
            "profile_summary": "",
        },
    )

    logger.info(
        "设置向导: Step1 session=%s target=%r type=%s industry=%r keywords=%s topics=%s%s",
        session_id[:8],
        target,
        subject_type,
        profile.get("industry", ""),
        keywords,
        monitoring_topics,
        " 缓存" if from_cache else "",
    )
    return {
        "session_id": session_id,
        "monitoring_topics": monitoring_topics,
    }


def discover_competitors_from_session(
    *,
    user_id: UUID,
    session_id: str,
    monitoring_topics: list[str],
) -> dict[str, Any]:
    """Step 2：搜索竞品并生成完整摘要，更新会话。"""
    _require_llm_key()

    session = get_session(user_id=str(user_id), session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    base = profile_from_dict(session.get("profile") or {})
    confirmed = session.get("micro_keywords") or []
    profile = merge_profile_updates(
        base,
        micro_keywords=confirmed if confirmed else None,
    )
    keywords = micro_keywords_list(profile)
    profile_dict = profile_to_dict(profile)
    confirmed_topics = monitoring_topics

    subject_type = session["subject_type"]
    region = session.get("region", "CN")
    language = session.get("language", "zh-CN")
    target = session["target"]
    fingerprint = competitors_search_fingerprint(
        subject_type=subject_type,
        target=target,
        micro_keywords=keywords,
    )

    cached = cached_competitors_result(session, fingerprint=fingerprint)
    if cached is not None:
        update_session(
            user_id=str(user_id),
            session_id=session_id,
            patch={
                "profile": profile_dict,
                "micro_keywords": keywords,
                "monitoring_topics": confirmed_topics,
            },
        )
        logger.info(
            "设置向导: 竞品缓存命中 session=%s competitors=%d",
            session_id[:8],
            len(cached["competitors"]),
        )
        return {"competitors": cached["competitors"]}

    research_payload = session.get("research_payload") or {}

    logger.info("设置向导: 搜索竞品 session=%s type=%s target=%r", session_id[:8], subject_type, target)
    t0 = time.perf_counter()

    if subject_type == "domain":
        result = search_domain_competitors(profile, target, region=region, language=language)
    else:
        web_research = research_payload.get("web_research") if isinstance(research_payload, dict) else None
        result = search_brand_competitors(
            profile,
            target,
            region=region,
            language=language,
            web_research=web_research if isinstance(web_research, list) else None,
        )

    profile_summary = run_profile_summary_stage(
        profile=profile,
        research_payload=research_payload,
        entity_key=target,
        region=region,
        subject_type=subject_type,
        competitors=result.get("competitors"),
    )
    competitors = result.get("competitors") or []
    update_session(
        user_id=str(user_id),
        session_id=session_id,
        patch=session_patch_after_competitors(
            profile_dict=profile_dict,
            keywords=keywords,
            confirmed_topics=confirmed_topics,
            profile_summary=profile_summary,
            fingerprint=fingerprint,
            competitors=competitors,
        ),
    )

    logger.info(
        "设置向导: 搜索结束 session=%s %.1fs competitors=%d summary=%d chars",
        session_id[:8],
        time.perf_counter() - t0,
        len(result.get("competitors") or []),
        len(profile_summary or ""),
    )
    return {"competitors": competitors}
