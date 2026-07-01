"""Tests for topic bind / pick / QA."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.topic_bind import bind_queries_to_topics
from aperix_geo.services.setup.topic_pick import fallback_topic_names_from_lexicon
from aperix_geo.services.setup.topic_qa import validate_topic_clusters


def _candidate(text: str, *, terms: list[str] | None = None) -> dict:
    return {
        "text": text,
        "intent": "commercial",
        "funnel": "mofu",
        "decision_type": "scenario_fit",
        "seed_terms": terms or [],
    }


def test_fallback_topic_names_from_lexicon_combines_scenario_category() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "高端绿茶",
            "topic_lexicon": {
                "category_terms": ["明前绿茶", "高端绿茶"],
                "scenario_terms": ["商务送礼", "家庭品饮"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
        },
        entity="竹叶青",
    )
    names = fallback_topic_names_from_lexicon(profile)
    assert len(names) == 5
    assert any("商务送礼" in n for n in names)
    assert any("明前" in n or "绿茶" in n for n in names)
    assert not any("认知" in n or "性价比" in n for n in names)


def test_bind_queries_to_topics_assigns_by_overlap() -> None:
    names = ["商务送礼绿茶", "明前高端绿茶", "企业礼盒茶", "家庭日常绿茶", "茶叶保鲜存放"]
    queries = [
        _candidate("商务场合送什么绿茶合适", terms=["商务送礼", "绿茶"]),
        _candidate("明前绿茶有哪些等级", terms=["明前绿茶"]),
        _candidate("企业采购茶叶礼盒怎么选", terms=["企业采购", "礼盒"]),
        _candidate("家里日常喝什么绿茶", terms=["家庭品饮", "绿茶"]),
        _candidate("高档绿茶怎么保存", terms=["茶叶保存", "绿茶"]),
    ]
    expanded = []
    for i, q in enumerate(queries * 4):
        expanded.append({**q, "text": f"{q['text']}（{i}）"})
    clusters = bind_queries_to_topics(names, expanded)
    assert len(clusters) == 5
    assert clusters[0]["name"] == "商务送礼绿茶"
    assert len(clusters[0]["seed_queries"]) >= 3


def test_validate_rejects_decision_dimension_topic_names() -> None:
    clusters = [
        {
            "name": name,
            "seed_queries": [
                {"text": f"{name}相关问句", "intent": "commercial", "funnel": "mofu", "decision_type": "price_value"}
            ]
            * 3,
        }
        for name in [
            "茶叶价格与性价比",
            "商务送礼绿茶",
            "明前高端绿茶",
            "企业礼盒茶",
            "家庭日常绿茶",
        ]
    ]
    with pytest.raises(ValueError, match="决策维度"):
        validate_topic_clusters(clusters, industry="高端绿茶", lexicon_terms=["商务送礼", "绿茶"])
