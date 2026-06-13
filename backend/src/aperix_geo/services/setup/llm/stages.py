"""Setup 向导 LLM 分步调用（Step1 画像 / 监测主题；Step2 摘要）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.profile import (
    fallback_monitoring_topics,
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
) -> tuple[NicheProfile, dict]:
    """Step1a：微观利基结构化画像（不含摘要、不含 monitoring_topics）。"""
    target = target.strip()
    research_payload = build_subject_research_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
    )
    temperature = 0.1 if subject_type == "domain" else 0.2
    data = generate_niche_profile_via_llm(
        entity_key=target,
        user_payload=research_payload,
        temperature=temperature,
    )
    profile = normalize_niche_profile(data, entity=target)
    return profile, research_payload


def run_monitoring_topics_stage(
    *,
    profile: NicheProfile,
    research_payload: dict,
    entity_key: str,
) -> list[str]:
    """Step1b：独立生成 monitoring_topics。"""
    payload = build_monitoring_topics_payload(
        research_payload=research_payload,
        profile=profile,
    )
    try:
        data = generate_monitoring_topics_via_llm(
            entity_key=entity_key,
            user_payload=payload,
        )
        topics = monitoring_topics_from_llm(data, profile)
    except Exception:
        logger.warning("Setup LLM 监测主题失败，使用规则回退", exc_info=True)
        topics = fallback_monitoring_topics(profile)

    return topics


def run_profile_summary_stage(
    *,
    profile: NicheProfile,
    research_payload: dict,
    entity_key: str,
    region: str,
    subject_type: str,
    competitors: list[dict[str, Any]] | None,
) -> str:
    """Step2：竞品搜索后生成完整 profile_summary。"""
    payload = build_profile_summary_payload(
        research_payload=research_payload,
        profile=profile,
        competitors=competitors,
    )
    try:
        summary = generate_profile_summary_via_llm(
            entity_key=entity_key,
            user_payload=payload,
        )
    except Exception:
        logger.warning("Setup LLM 主体摘要失败，使用模板回退", exc_info=True)
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
        "Setup LLM 主体摘要: entity=%r chars=%d",
        entity_key,
        len(summary),
    )
    return summary


def build_subject_profile(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
) -> tuple[NicheProfile, list[str], dict]:
    """设置向导 Step1：微观利基画像 + 监测主题（两次 LLM；摘要移至竞品搜索后）。"""
    profile, research_payload = run_niche_profile_stage(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
    )
    monitoring_topics = run_monitoring_topics_stage(
        profile=profile,
        research_payload=research_payload,
        entity_key=target.strip(),
    )
    return profile, monitoring_topics, research_payload
