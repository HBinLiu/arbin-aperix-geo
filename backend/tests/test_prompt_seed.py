"""Tests for seed-first setup prompt generation (keyword_plan fallback)."""

from __future__ import annotations

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.prompts.constants import PROMPT_PER_TOPIC
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.prompt_qa import validate_generated_prompts
from aperix_geo.services.setup.prompt_seed import build_prompts_for_topic, build_prompts_from_plan


def _profile(*, topic: str = "跨境支付") -> dict:
    return normalize_niche_profile(
        {
            "industry": "金融科技",
            "keywords": [topic, "跨境收款", "全球账户"],
            "brief": "出海企业",
        },
        entity="example.com",
    )


def test_build_prompts_from_plan_passes_qa() -> None:
    topic = "跨境支付"
    profile = _profile(topic=topic)
    plan = build_keyword_plan(profile)
    rows = build_prompts_from_plan(
        topics=[topic],
        profile=profile,
        plan=plan,
        limit=PROMPT_PER_TOPIC,
    )
    assert len(rows) == 1
    assert len(rows[0]["prompts"]) == PROMPT_PER_TOPIC
    texts = [p["text"] for p in rows[0]["prompts"]]
    assert len(set(texts)) == len(texts)
    assert any(topic in t for t in texts)
    validate_generated_prompts(rows)


def test_build_prompts_for_topic_respects_exclude() -> None:
    topic = "跨境支付"
    profile = _profile(topic=topic)
    plan = build_keyword_plan(profile)
    all_texts = [
        p["text"]
        for p in build_prompts_for_topic(
            topic=topic,
            plan=plan,
            limit=PROMPT_PER_TOPIC,
            excluded=set(),
        )
    ]
    assert len(all_texts) == PROMPT_PER_TOPIC
    blocked = all_texts[0]
    prompts = build_prompts_for_topic(
        topic=topic,
        plan=plan,
        limit=PROMPT_PER_TOPIC,
        excluded={blocked},
    )
    texts = [p["text"] for p in prompts]
    assert blocked not in texts
    assert any(topic in t for t in texts)


def test_build_prompts_from_plan_multiple_topics() -> None:
    topic = "多平台GEO监测"
    profile = normalize_niche_profile(
        {
            "industry": "GEO",
            "keywords": [topic, "品牌搜索可见度", "品牌引用分析"],
            "brief": "市场团队",
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    prompts = build_prompts_for_topic(
        topic=topic,
        plan=plan,
        limit=PROMPT_PER_TOPIC,
        excluded=set(),
    )
    assert len(prompts) == PROMPT_PER_TOPIC
    texts = [p["text"] for p in prompts]
    assert len(set(texts)) == len(texts)
