"""Tests for setup prompt QA helpers."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.prompt_qa import (
    prompt_contains_punctuation,
    strip_prompt_punctuation,
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
            "search_queries": [f"{topic}商务送礼企业采购"],
        },
        entity="tea.com",
    )


def test_strip_prompt_punctuation() -> None:
    assert strip_prompt_punctuation("商务送礼选什么茶？") == "商务送礼选什么茶"
    assert strip_prompt_punctuation("岩茶礼盒，怎么选") == "岩茶礼盒怎么选"
    assert strip_prompt_punctuation("What is GEO?") == "What is GEO"


def test_validate_rejects_punctuation() -> None:
    profile = _prompt_profile()
    with pytest.raises(ValueError, match="不得含标点"):
        validate_generated_prompts(
            [
                {
                    "topic": "铁观音",
                    "prompts": [
                        {
                            "text": "商务场合送什么茶？",
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
                        "text": "铁观音商务送礼茶叶保存方法",
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


def test_prompt_contains_punctuation() -> None:
    assert prompt_contains_punctuation("有问号吗？")
    assert not prompt_contains_punctuation("没有标点")


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
                "AI可见度监测市场团队工具",
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
                            "text": "AI可见度监测AI引用率对比方案",
                            "funnel_stage": "bofu",
                            "search_intent": "commercial",
                            "decision_type": "solution_comparison",
                        },
                        {
                            "text": "AI可见度监测市场团队选型差异",
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
                            "text": "品牌搜索可见度AI引用率对比方案",
                            "funnel_stage": "bofu",
                            "search_intent": "commercial",
                            "decision_type": "solution_comparison",
                        },
                        {
                            "text": "品牌搜索可见度市场团队选型差异",
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
