"""Setup 向导 LLM 分步调用（discover 画像 / topics 主题+摘要）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.profile import (
    monitoring_topics_from_llm,
    normalize_niche_profile,
    region_label,
)
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    generate_monitoring_topics_via_llm,
    generate_niche_profile_via_llm,
    generate_profile_summary_via_llm,
    merge_competitors_into_summary,
)
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.llm.payloads import (
    build_monitoring_topics_payload,
    build_profile_summary_payload,
    build_subject_research_payload,
)

logger = logging.getLogger(__name__)


def run_niche_profile_stage(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
) -> tuple[NicheProfile, dict, dict[str, Any]]:
    """UI Step 0→1 discover：微观利基结构化画像。"""
    target = target.strip()
    research_payload = build_subject_research_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
    )
    temperature = 0.1 if subject_type == "domain" else 0.2
    data, usage = generate_niche_profile_via_llm(
        entity_key=target,
        user_payload=research_payload,
        temperature=temperature,
    )
    profile = normalize_niche_profile(data, entity=target)
    return profile, research_payload, usage


def run_monitoring_topics_stage(
    *,
    profile: NicheProfile,
    subject_type: str,
    entity_key: str,
) -> tuple[list[str], dict[str, Any]]:
    """UI Step 1→2 topics：监测主题建议（先于 profile_summary）。"""
    payload = build_monitoring_topics_payload(
        subject_type=subject_type,
        target=entity_key,
        profile=profile,
    )
    data, usage = generate_monitoring_topics_via_llm(
        entity_key=entity_key,
        user_payload=payload,
    )
    return monitoring_topics_from_llm(data), usage


def run_profile_summary_stage(
    *,
    profile: NicheProfile,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    entity_key: str,
    competitors: list[dict[str, Any]] | None,
) -> tuple[str, dict[str, Any]]:
    """UI Step 1→2 topics：用户确认竞品后生成 profile_summary（在监测主题之后）。"""
    payload = build_profile_summary_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        profile=profile,
        competitors=competitors,
    )
    usage: dict[str, Any] = {}
    try:
        summary, usage = generate_profile_summary_via_llm(
            entity_key=entity_key,
            user_payload=payload,
        )
    except Exception:
        logger.warning("设置向导·主题 主体摘要 LLM 失败，使用模板回退", exc_info=True)
        summary = ""

    if not summary:
        summary = fallback_profile_summary(
            profile,
            entity=entity_key,
            region_label=region_label(region),
        )
        summary = merge_competitors_into_summary(
            summary,
            subject_type=subject_type,
            competitors=competitors,
        )
    logger.info(
        "设置向导·主题·摘要 entity=%r 字数=%d",
        entity_key,
        len(summary),
    )
    return summary, usage
