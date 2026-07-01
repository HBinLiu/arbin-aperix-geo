"""Setup 向导 LLM 分步调用（discover 画像 / topics 主题+摘要）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.profile import (
    normalize_niche_profile,
    parse_candidate_queries,
    region_label,
    topic_lexicon_dict,
)
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    generate_profile_summary_via_llm,
    generate_query_expand_via_llm,
    generate_topic_pick_via_llm,
    generate_niche_profile_via_llm,
    merge_competitors_into_summary,
    merge_llm_usage,
)
from aperix_geo.services.competitor.topic_types import TopicCluster
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.llm.payloads import (
    build_profile_summary_payload,
    build_query_expand_payload,
    build_subject_research_payload,
    build_topic_pick_payload,
)
from aperix_geo.services.setup.topic_bind import bind_queries_to_topics
from aperix_geo.services.setup.topic_pick import fallback_topic_names_from_lexicon, parse_topic_names
from aperix_geo.services.setup.topic_qa import validate_topic_clusters

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
    data, usage = generate_niche_profile_via_llm(
        entity_key=target,
        user_payload=research_payload,
    )
    profile = normalize_niche_profile(data, entity=target)
    return profile, research_payload, usage


def _competitor_scenarios(competitors: list[dict[str, Any]] | None) -> list[str]:
    scenarios: list[str] = []
    seen: set[str] = set()
    for item in competitors or []:
        for field in ("summary", "brand"):
            text = str(item.get(field) or "").strip()
            if not text or len(text) < 4:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            scenarios.append(text[:120])
    return scenarios[:8]


def run_topic_generation_stage(
    *,
    profile: NicheProfile,
    subject_type: str,
    entity_key: str,
    competitors: list[dict[str, Any]] | None = None,
) -> tuple[list[TopicCluster], list[dict[str, Any]], dict[str, Any]]:
    """UI Step 1→2 topics：问句扩词 → 词表定靶心 → 问句绑定 → QA。"""
    expand_payload = build_query_expand_payload(
        subject_type=subject_type,
        target=entity_key,
        profile=profile,
        competitor_scenarios=_competitor_scenarios(competitors),
    )
    expand_data, expand_usage = generate_query_expand_via_llm(
        entity_key=entity_key,
        user_payload=expand_payload,
    )
    candidate_queries = parse_candidate_queries(expand_data)
    if len(candidate_queries) < 15:
        raise ValueError("候选问句不足，无法生成监测主题")

    lexicon = topic_lexicon_dict(profile)
    lexicon_terms = [
        *lexicon.get("category_terms", []),
        *lexicon.get("scenario_terms", []),
        *lexicon.get("audience_terms", []),
        *lexicon.get("pain_terms", []),
    ]

    pick_payload = build_topic_pick_payload(
        subject_type=subject_type,
        target=entity_key,
        profile=profile,
    )
    pick_data, pick_usage = generate_topic_pick_via_llm(
        entity_key=entity_key,
        user_payload=pick_payload,
    )
    topic_names = parse_topic_names(pick_data)
    if len(topic_names) != 5:
        logger.warning(
            "Setup 主题选定 LLM 条数异常 entity=%r count=%d，使用 lexicon 回退",
            entity_key,
            len(topic_names),
        )
        topic_names = fallback_topic_names_from_lexicon(profile)
    if len(topic_names) != 5:
        raise ValueError("无法从词表生成 5 个监测主题")

    topic_clusters = bind_queries_to_topics(topic_names, candidate_queries)
    validate_topic_clusters(
        topic_clusters,
        industry=str(profile.get("industry") or ""),
        lexicon_terms=lexicon_terms,
    )

    usage = merge_llm_usage(expand_usage, pick_usage)
    candidate_payload = [dict(q) for q in candidate_queries]
    return topic_clusters, candidate_payload, usage


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
