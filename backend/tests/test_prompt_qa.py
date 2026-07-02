"""Tests for setup prompt QA helpers."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.prompt_qa import (
    collect_prompt_quality_feedback,
    validate_generated_prompts,
)


def _prompt_profile(*, topic: str = "铁观音") -> dict:
    return normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": [topic, "岩茶", "高端红茶"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": [f"{topic}商务送礼企业采购怎么选"],
        },
        entity="tea.com",
    )


def test_validate_accepts_punctuation() -> None:
    profile = _prompt_profile()
    validate_generated_prompts(
        [
            {
                "topic": "铁观音",
                "prompts": [
                    {
                        "text": "商务场合送铁观音什么茶？",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    }
                ],
            }
        ],
        keyword_plan=build_keyword_plan(profile),
        min_types=1,
    )


def test_collect_prompt_quality_feedback_flags_insufficient_skeleton_kinds() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["GEO品牌监测"],
                "scenario_terms": ["多平台对比分析"],
                "audience_terms": ["品牌营销人员"],
                "pain_terms": ["难以量化可见度"],
            },
            "search_queries": ["GEO品牌监测品牌营销人员怎么做"],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    same_suffix = "GEO品牌监测多平台对比分析怎么做"
    items = [
        {
            "topic": "GEO品牌监测",
            "prompts": [
                {"text": same_suffix, "funnel_stage": "mofu", "search_intent": "commercial", "decision_type": "solution_comparison"},
                {"text": same_suffix, "funnel_stage": "mofu", "search_intent": "commercial", "decision_type": "scenario_fit"},
                {"text": same_suffix, "funnel_stage": "mofu", "search_intent": "commercial", "decision_type": "price_value"},
                {"text": same_suffix, "funnel_stage": "mofu", "search_intent": "informational", "decision_type": "trust_risk"},
            ],
        },
    ]
    feedback = collect_prompt_quality_feedback(items, keyword_plan=plan)
    assert any("句法骨架仅" in line for line in feedback)


def test_validate_accepts_title_like_text_without_hard_tone_check() -> None:
    profile = _prompt_profile()
    validate_generated_prompts(
        [
            {
                "topic": "铁观音",
                "prompts": [
                    {
                        "text": "铁观音商务送礼基础概念",
                        "funnel_stage": "tofu",
                        "search_intent": "informational",
                        "decision_type": "category_awareness",
                    }
                ],
            }
        ],
        keyword_plan=build_keyword_plan(profile),
        min_types=1,
    )


def test_validate_accepts_plain_text() -> None:
    profile = _prompt_profile()
    validate_generated_prompts(
        [
            {
                "topic": "铁观音",
                "prompts": [
                    {
                        "text": "商务送礼铁观音怎么选合适",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    },
                    {
                        "text": "企业采购铁观音商务送礼怎么选",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "solution_comparison",
                    },
                    {
                        "text": "铁观音商务送礼茶叶怎么保存",
                        "funnel_stage": "bofu",
                        "search_intent": "transactional",
                        "decision_type": "price_value",
                    },
                    {
                        "text": "如何判断铁观音商务送礼品质",
                        "funnel_stage": "mofu",
                        "search_intent": "informational",
                        "decision_type": "trust_risk",
                    },
                ],
            }
        ],
        keyword_plan=build_keyword_plan(profile),
        min_types=4,
    )


def test_validate_rejects_topic_without_resolved_core() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": ["AI可见度监测市场团队工具"],
        },
        entity="example.com",
    )
    with pytest.raises(ValueError, match="须完整包含 keyword_plan 核心词"):
        validate_generated_prompts(
            [
                {
                    "topic": "品牌可见度监控",
                    "prompts": [
                        {
                            "text": "AI可见度监测市场团队工具",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "scenario_fit",
                        }
                    ],
                }
            ],
            keyword_plan=build_keyword_plan(profile),
            min_types=1,
        )


def test_validate_rejects_cross_topic_duplicate_skeleton() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具怎么选",
                "品牌搜索可见度多平台监测评估",
                "品牌引用分析AI引用率评估",
            ],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    with pytest.raises(ValueError, match="跨主题句式重复"):
        validate_generated_prompts(
            [
                {
                    "topic": "AI可见度监测",
                    "prompts": [
                        {
                            "text": "AI可见度监测市场团队怎么选",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "scenario_fit",
                        },
                        {
                            "text": "AI可见度监测多平台监测怎么评估",
                            "funnel_stage": "mofu",
                            "search_intent": "informational",
                            "decision_type": "trust_risk",
                        },
                        {
                            "text": "AI可见度监测AI引用率怎么对比",
                            "funnel_stage": "bofu",
                            "search_intent": "commercial",
                            "decision_type": "solution_comparison",
                        },
                        {
                            "text": "AI可见度监测市场团队怎么选型",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "price_value",
                        },
                    ],
                },
                {
                    "topic": "品牌搜索可见度",
                    "prompts": [
                        {
                            "text": "品牌搜索可见度市场团队怎么选",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "scenario_fit",
                        },
                        {
                            "text": "品牌搜索可见度多平台监测怎么评估",
                            "funnel_stage": "mofu",
                            "search_intent": "informational",
                            "decision_type": "trust_risk",
                        },
                        {
                            "text": "品牌搜索可见度AI引用率怎么对比",
                            "funnel_stage": "bofu",
                            "search_intent": "commercial",
                            "decision_type": "solution_comparison",
                        },
                        {
                            "text": "品牌搜索可见度市场团队怎么选型",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "price_value",
                        },
                    ],
                },
            ],
            keyword_plan=plan,
            min_types=4,
            strict_quality=True,
        )


def test_validate_default_mode_tolerates_cross_topic_skeleton() -> None:
    profile = normalize_niche_profile(
        {
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
    validate_generated_prompts(
        [
            {
                "topic": "AI可见度监测",
                "prompts": [
                    {
                        "text": "AI可见度监测市场团队怎么选",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    }
                ],
            },
            {
                "topic": "品牌搜索可见度",
                "prompts": [
                    {
                        "text": "品牌搜索可见度市场团队怎么选",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    }
                ],
            },
        ],
        keyword_plan=plan,
        min_types=1,
    )
