"""Tests for keyword plan against slim niche profile."""

from __future__ import annotations

from aperix_geo.services.competitor.profile import keywords_list, normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import (
    build_keyword_plan,
    match_core_keyword,
    prompt_text_skeleton,
)
from aperix_geo.services.setup.materials import assert_niche_profile_sufficient, is_niche_profile_sufficient


def test_build_keyword_plan_from_keywords() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测",
            "keywords": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析"],
            "brief": "市场团队",
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    assert "AI可见度监测" in plan["core_keywords"]
    assert "品牌引用分析" in plan["core_keywords"]
    # 每 core 5 条模板；至少覆盖前几个 core
    assert len(plan["long_tail_examples"]) >= 5
    assert any("AI可见度监测怎么选合适" == t for t in plan["long_tail_examples"])


def test_prompt_text_skeleton_strips_core() -> None:
    skeleton = prompt_text_skeleton(
        "AI可见度监测怎么选",
        core="AI可见度监测",
    )
    assert "AI可见度监测" not in skeleton


def test_match_core_keyword() -> None:
    assert match_core_keyword("跨境收款怎么选", ["跨境收款", "换汇"]) == "跨境收款"


def test_niche_profile_sufficient_slim() -> None:
    profile = normalize_niche_profile(
        {"industry": "跨境支付", "keywords": ["跨境收款"], "brief": ""},
        entity="x",
    )
    assert is_niche_profile_sufficient(profile) is True
    assert_niche_profile_sufficient(profile)


def test_keywords_list_roundtrip() -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": ["可见度", "提及率"], "brief": "市场部"},
        entity="x",
    )
    assert keywords_list(profile) == ["可见度", "提及率"]
