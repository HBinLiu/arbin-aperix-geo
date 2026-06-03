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
    build_subject_profile,
    language_label,
    merge_profile_updates,
    micro_keywords_list,
    profile_from_dict,
    profile_to_dict,
    region_label,
)
from aperix_geo.services.competitor.summary import finalize_profile_summary
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.setup.session import create_session, get_session, update_session

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
    """Step 1：生成微观利基画像 + 摘要，写入 Redis 会话。"""
    _require_llm_key()

    if subject_type == "domain":
        if not domain:
            raise ValueError("domain is required for domain subject type")
        target = registrable_domain(domain)
    else:
        if not brand or not brand.strip():
            raise ValueError("brand is required for brand subject type")
        target = brand.strip()

    profile, profile_summary = build_subject_profile(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
    )

    keywords = micro_keywords_list(profile) or ([target] if target else [])
    profile_dict = profile_to_dict(profile)

    session_id = create_session(
        user_id=str(user_id),
        payload={
            "subject_type": subject_type,
            "target": target,
            "domain": target if subject_type == "domain" else None,
            "brand": target if subject_type == "brand" else None,
            "region": region,
            "language": language,
            "profile": profile_dict,
            "micro_keywords": keywords,
            "profile_summary": profile_summary,
        },
    )

    logger.info(
        "设置向导: 画像 session=%s type=%s target=%r keywords=%s summary=%d chars",
        session_id[:8],
        subject_type,
        target,
        keywords,
        len(profile_summary or ""),
    )
    return {
        "session_id": session_id,
        "micro_keywords": keywords,
    }


def discover_competitors_from_session(
    *,
    user_id: UUID,
    session_id: str,
    micro_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Step 2：搜索竞品，回写并 enrich 摘要，更新会话。"""
    _require_llm_key()

    session = get_session(user_id=str(user_id), session_id=session_id)
    if session is None:
        raise ValueError("setup session not found or expired")

    base = profile_from_dict(session.get("profile") or {})
    confirmed = micro_keywords if micro_keywords is not None else session.get("micro_keywords") or []
    profile = merge_profile_updates(
        base,
        micro_keywords=confirmed if confirmed else None,
    )
    keywords = micro_keywords_list(profile)
    profile_dict = profile_to_dict(profile)

    subject_type = session["subject_type"]
    region = session.get("region", "CN")
    language = session.get("language", "zh-CN")
    target = session["target"]

    logger.info("设置向导: 搜索竞品 session=%s type=%s target=%r", session_id[:8], subject_type, target)
    t0 = time.perf_counter()

    if subject_type == "domain":
        result = search_domain_competitors(profile, target)
    else:
        result = search_brand_competitors(profile, target, region=region, language=language)

    result["micro_keywords"] = keywords
    result["session_id"] = session_id

    profile_summary = finalize_profile_summary(
        session.get("profile_summary"),
        profile_fields=profile_dict,
        subject_type=subject_type,
        competitors=result.get("competitors"),
        brand_names=result.get("brand_names"),
        region_label=region_label(region),
        language_label=language_label(language),
    )

    update_session(
        user_id=str(user_id),
        session_id=session_id,
        patch={
            "profile": profile_dict,
            "micro_keywords": keywords,
            "profile_summary": profile_summary,
            "last_competitors": {
                "domains": result.get("domains", []),
                "competitors": result.get("competitors", []),
                "brand_names": result.get("brand_names", []),
            },
        },
    )

    logger.info(
        "设置向导: 搜索结束 session=%s %.1fs domains=%s brands=%s",
        session_id[:8],
        time.perf_counter() - t0,
        result.get("domains"),
        result.get("brand_names"),
    )
    return result
