"""Tests for SEO keyword plan and profile lexicon QA."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile, topic_lexicon_dict
from aperix_geo.services.setup.keyword_plan import (
    build_keyword_plan,
    dedupe_substring_terms,
    is_modifier_only_category_term,
    match_core_keyword,
    match_modifier,
    prompt_text_skeleton,
    seed_candidates_from_plan,
    topic_modifiers_for_core,
)
from aperix_geo.services.setup.profile_qa import repair_profile_search_queries, validate_profile_lexicon


def test_topic_modifiers_for_core_rotates_by_topic_index() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具",
                "品牌搜索可见度多平台监测",
                "品牌引用分析AI引用率评估",
            ],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    first = topic_modifiers_for_core("AI可见度监测", plan=plan, topic_index=0)
    second = topic_modifiers_for_core("品牌搜索可见度", plan=plan, topic_index=1)
    assert first[0] != second[0] or first[:2] != second[:2]


def test_prompt_text_skeleton_strips_core_and_modifiers() -> None:
    skeleton = prompt_text_skeleton(
        "AI可见度监测市场团队怎么选",
        core="AI可见度监测",
        modifiers=["市场团队", "多平台监测"],
    )
    assert "AI可见度监测" not in skeleton
    assert "市场团队" not in skeleton
    assert skeleton == "怎么选"


def test_build_keyword_plan_merges_category_and_features() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["品牌引用分析"],
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": ["AI可见度监测市场团队工具"],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    assert "AI可见度监测" in plan["core_keywords"]
    assert "品牌引用分析" in plan["core_keywords"]
    assert match_core_keyword("AI可见度监测多平台", plan["core_keywords"]) == "AI可见度监测"
    assert match_modifier("AI可见度监测市场团队", plan["all_modifiers"]) == "市场团队"


def test_match_core_keyword_ignores_whitespace() -> None:
    core = ["AI 可见度监测", "品牌搜索可见度", "GEO监测平台"]
    assert match_core_keyword("AI可见度监测市场团队", core) == "AI 可见度监测"


def test_validate_profile_lexicon_accepts_spaced_core_in_compact_query() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["品牌引用分析"],
            "topic_lexicon": {
                "category_terms": [
                    "AI 可见度监测",
                    "品牌搜索可见度",
                    "GEO监测平台",
                    "品牌引用分析",
                    "多平台GEO监测",
                ],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具怎么选",
                "品牌搜索可见度多平台监测",
                "GEO监测平台AI引用率评估",
                "品牌引用分析市场团队怎么看",
                "多平台GEO监测配置方法",
            ],
        },
        entity="aibase.com",
    )
    validate_profile_lexicon(profile)


def test_repair_profile_search_queries_prepends_core_when_drifted() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["AI品牌可见度", "引用率分析", "多平台监测"],
            "topic_lexicon": {
                "category_terms": [
                    "AI品牌可见度",
                    "GEO监测系统",
                    "引用率分析",
                    "品牌搜索可见度",
                    "多平台GEO监测",
                ],
                "scenario_terms": ["AI搜索排名"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["品牌心智份额"],
            },
            "search_queries": [
                "品牌心智份额AI搜索排名提升怎么做",
                "AI品牌可见度市场团队工具",
                "GEO监测系统配置方法",
                "引用率分析怎么算",
                "品牌搜索可见度多平台监测",
            ],
        },
        entity="aibase.com",
    )
    repaired = repair_profile_search_queries(profile)
    validate_profile_lexicon(repaired)
    fixed = repaired.get("search_queries", "")
    assert "AI品牌可见度" in fixed or "GEO监测系统" in fixed or "引用率分析" in fixed


def test_dedupe_substring_terms_drops_shorter_head() -> None:
    assert dedupe_substring_terms(["品牌提及率", "品牌提及率分析", "AI可见度监测"]) == [
        "品牌提及率分析",
        "AI可见度监测",
    ]


def test_is_modifier_only_category_term() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "竞品对标"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具",
            ],
        },
        entity="example.com",
    )
    assert is_modifier_only_category_term("竞品对标", profile=profile)
    assert not is_modifier_only_category_term("AI可见度监测", profile=profile)


def test_seed_candidates_from_plan_filters_by_core_and_modifier() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具",
                "品牌搜索可见度多平台监测",
                "AI可见度监测多平台监测评估",
            ],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    preferred = topic_modifiers_for_core("AI可见度监测", plan=plan, topic_index=0)
    candidates = seed_candidates_from_plan(
        "AI可见度监测",
        plan=plan,
        preferred_modifiers=preferred,
    )
    assert "AI可见度监测市场团队工具" in candidates
    assert "AI可见度监测多平台监测评估" in candidates
    assert "品牌搜索可见度多平台监测" not in candidates
    assert all("AI可见度监测" in c for c in candidates)


def test_validate_profile_lexicon_rejects_weak_core_set() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "茶叶",
            "topic_lexicon": {
                "category_terms": ["铁观音"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": ["铁观音商务送礼"],
        },
        entity="tea.com",
    )
    with pytest.raises(ValueError, match="核心词不足"):
        validate_profile_lexicon(profile)
