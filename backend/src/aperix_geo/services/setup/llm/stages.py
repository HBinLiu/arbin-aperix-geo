"""Setup 向导 LLM 分步调用（discover 画像 / topics 主题+摘要）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.profile import normalize_niche_profile, region_label
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    generate_niche_profile_via_llm,
    generate_profile_summary_via_llm,
    generate_topic_plan_via_llm,
    merge_competitors_into_summary,
)
from aperix_geo.services.competitor.topic_types import TopicCluster
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.llm.payloads import (
    build_profile_summary_payload,
    build_subject_research_payload,
    build_topic_plan_payload,
)
from aperix_geo.services.setup.profile_qa import (
    repair_profile_search_queries,
    sanitize_profile_lexicon,
    validate_profile_lexicon,
)
from aperix_geo.services.setup.topic_bind import bind_topic_clusters_to_cores
from aperix_geo.services.setup.topic_parse import parse_topic_plan_response
from aperix_geo.services.setup.topic_qa import collect_subject_names, validate_topic_clusters

logger = logging.getLogger(__name__)


def run_niche_profile_stage(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
    user_corpus: str = "",
    homepage_text: str = "",
    homepage_metadata: dict[str, str] | None = None,
) -> tuple[NicheProfile, dict, dict[str, Any]]:
    """UI Step 0→1 discover：微观利基结构化画像。"""
    target = target.strip()
    research_payload = build_subject_research_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
        user_corpus=user_corpus,
        homepage_text=homepage_text,
        homepage_metadata=homepage_metadata,
    )
    usage: dict[str, Any] = {}
    last_error: Exception | None = None
    validation_feedback: list[str] = []
    for attempt in range(2):
        try:
            user_payload = dict(research_payload)
            if validation_feedback:
                user_payload["validation_feedback"] = validation_feedback
            data, call_usage = generate_niche_profile_via_llm(
                entity_key=target,
                user_payload=user_payload,
            )
            usage = call_usage
            profile = normalize_niche_profile(data, entity=target)
            profile = repair_profile_search_queries(profile)
            profile = sanitize_profile_lexicon(profile)
            validate_profile_lexicon(profile)
            return profile, research_payload, usage
        except ValueError as exc:
            last_error = exc
            validation_feedback = [str(exc)]
            logger.warning(
                "Setup 微观利基画像校验未通过 target=%r attempt=%d: %s",
                target,
                attempt + 1,
                exc,
            )

    raise ValueError(f"微观利基画像失败：{last_error}") from last_error


def run_topic_generation_stage(
    *,
    profile: NicheProfile,
    subject_type: str,
    entity_key: str,
    competitors: list[dict[str, Any]] | None = None,
) -> tuple[list[TopicCluster], dict[str, Any]]:
    """UI Step 1→2 topics：topic_plan LLM → 解析归一化 → 结构校验（失败重试 1 次）。"""
    validate_profile_lexicon(profile)
    subject_names = collect_subject_names(
        profile_company=str(profile.get("company") or ""),
        entity_key=entity_key,
        competitors=competitors,
    )

    usage: dict[str, Any] = {}
    last_error: Exception | None = None
    validation_feedback: list[str] = []
    payload = build_topic_plan_payload(
        subject_type=subject_type,
        target=entity_key,
        profile=profile,
        competitors=competitors,
    )
    for attempt in range(2):
        try:
            if validation_feedback:
                payload = build_topic_plan_payload(
                    subject_type=subject_type,
                    target=entity_key,
                    profile=profile,
                    competitors=competitors,
                    validation_feedback=validation_feedback,
                )
            data, call_usage = generate_topic_plan_via_llm(
                entity_key=entity_key,
                user_payload=payload,
            )
            usage = call_usage
            clusters = parse_topic_plan_response(data)
            clusters = bind_topic_clusters_to_cores(clusters, profile=profile)
            validate_topic_clusters(
                clusters,
                subject_names=subject_names,
                profile=profile,
            )
            return clusters, usage
        except ValueError as exc:
            last_error = exc
            validation_feedback = [str(exc)]
            logger.warning(
                "Setup 主题规划校验未通过 entity=%r attempt=%d: %s",
                entity_key,
                attempt + 1,
                exc,
            )

    raise ValueError(f"主题规划失败：{last_error}") from last_error


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
