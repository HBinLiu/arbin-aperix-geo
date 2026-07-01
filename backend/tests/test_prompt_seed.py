"""Tests for seed-first setup prompt generation."""

from __future__ import annotations

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.prompt_seed import build_prompts_for_topic, build_prompts_from_seeds
from aperix_geo.services.setup.prompt_qa import validate_generated_prompts


def _profile(*, topic: str = "跨境支付") -> dict:
    return normalize_niche_profile(
        {
            "industry": "金融科技",
            "features": "API",
            "customers": "出海企业",
            "topic_lexicon": {
                "category_terms": [topic, "跨境收款", "全球账户"],
                "scenario_terms": ["出海企业"],
                "audience_terms": ["中小企业"],
                "pain_terms": ["合规结汇"],
            },
            "search_queries": [
                f"{topic}出海企业合规结汇",
                f"{topic}中小企业对比方案",
                f"{topic}全球账户怎么选",
                f"{topic}合规结汇怎么评估",
            ],
        },
        entity="example.com",
    )


def _clusters(topic: str) -> list[dict]:
    return [
        {
            "name": topic,
            "seed_queries": [
                {
                    "text": f"{topic}出海企业怎么选",
                    "funnel": "mofu",
                    "intent": "commercial",
                    "decision": "scenario_fit",
                },
                {
                    "text": f"{topic}合规结汇怎么评估",
                    "funnel": "mofu",
                    "intent": "informational",
                    "decision": "trust_risk",
                },
                {
                    "text": f"{topic}中小企业对比方案",
                    "funnel": "bofu",
                    "intent": "commercial",
                    "decision": "solution_comparison",
                },
            ],
        }
    ]


def test_build_prompts_from_seeds_passes_qa() -> None:
    topic = "跨境支付"
    profile = _profile(topic=topic)
    plan = build_keyword_plan(profile)
    rows = build_prompts_from_seeds(
        topics=[topic],
        topic_clusters=_clusters(topic),
        profile=profile,
        limit=10,
    )
    assert len(rows) == 1
    assert 3 <= len(rows[0]["prompts"]) <= 10
    texts = [p["text"] for p in rows[0]["prompts"]]
    assert len(set(texts)) == len(texts)
    validate_generated_prompts(
        rows,
        keyword_plan=plan,
        topic_clusters=_clusters(topic),
    )


def test_build_prompts_for_topic_respects_exclude() -> None:
    topic = "跨境支付"
    profile = _profile(topic=topic)
    prompts = build_prompts_for_topic(
        topic=topic,
        topic_clusters=_clusters(topic),
        profile=profile,
        topic_index=0,
        limit=10,
        excluded={"跨境支付出海企业怎么选"},
    )
    texts = [p["text"] for p in prompts]
    assert "跨境支付出海企业怎么选" not in texts
    assert any("跨境支付" in t for t in texts)


def test_build_prompts_does_not_pad_with_suffix_variants() -> None:
    topic = "多平台GEO监测"
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": [topic, "品牌搜索可见度", "品牌引用分析"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "多平台GEO监测市场团队工具",
                "多平台GEO监测AI引用率评估",
                "多平台GEO监测竞品对标差异",
            ],
        },
        entity="example.com",
    )
    clusters = [
        {
            "name": topic,
            "seed_queries": [
                {
                    "text": f"{topic}市场团队怎么选",
                    "funnel": "mofu",
                    "intent": "commercial",
                    "decision": "scenario_fit",
                },
            ],
        }
    ]
    prompts = build_prompts_for_topic(
        topic=topic,
        topic_clusters=clusters,
        profile=profile,
        topic_index=0,
        limit=10,
        excluded=set(),
    )
    assert 1 < len(prompts) <= 10
    texts = [p["text"] for p in prompts]
    assert len(set(texts)) == len(texts)
    assert not any(t.endswith("选型差异") or t.endswith("注意事项") for t in texts)
