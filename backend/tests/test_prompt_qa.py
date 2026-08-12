"""Tests for setup prompt QA helpers."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.prompt_qa import validate_generated_prompts


def test_validate_accepts_natural_phrasing_without_exact_core() -> None:
    """默认模式不要求问句完整包含主题核心词连写。"""
    validate_generated_prompts(
        [
            {
                "topic": "冠心病中成药",
                "prompts": [
                    {
                        "text": "治疗冠心病的中成药有哪些？",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    }
                ],
            }
        ],
    )


def test_validate_accepts_punctuation() -> None:
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
    )


def test_validate_accepts_title_like_text_without_hard_tone_check() -> None:
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
    )


def test_validate_accepts_plain_text() -> None:
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
    )


def test_validate_default_allows_topic_without_resolved_core() -> None:
    validate_generated_prompts(
        [
            {
                "topic": "品牌可见度监控",
                "prompts": [
                    {
                        "text": "品牌可见度怎么评估合适",
                        "funnel_stage": "mofu",
                        "search_intent": "commercial",
                        "decision_type": "scenario_fit",
                    }
                ],
            }
        ],
    )


def test_strict_quality_rejects_topic_without_resolved_core() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "keywords": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析"],
            "brief": "市场团队",
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
            strict_quality=True,
        )


def test_strict_quality_rejects_missing_core_in_text() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "中成药",
            "keywords": ["冠心病中成药"],
            "brief": "心脑血管",
        },
        entity="x",
    )
    with pytest.raises(ValueError, match="须含主题核心词"):
        validate_generated_prompts(
            [
                {
                    "topic": "冠心病中成药",
                    "prompts": [
                        {
                            "text": "治疗冠心病的中成药有哪些？",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "scenario_fit",
                        }
                    ],
                }
            ],
            keyword_plan=build_keyword_plan(profile),
            min_types=1,
            strict_quality=True,
        )


def test_validate_default_tolerates_cross_topic_skeleton() -> None:
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
    )


def test_strict_quality_rejects_cross_topic_skeleton() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO",
            "keywords": ["AI可见度监测", "品牌搜索可见度"],
            "brief": "市场团队",
        },
        entity="example.com",
    )
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
            keyword_plan=build_keyword_plan(profile),
            min_types=1,
            strict_quality=True,
        )


def test_validate_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="空提示词"):
        validate_generated_prompts(
            [
                {
                    "topic": "铁观音",
                    "prompts": [
                        {
                            "text": "  ",
                            "funnel_stage": "mofu",
                            "search_intent": "commercial",
                            "decision_type": "scenario_fit",
                        }
                    ],
                }
            ],
        )
