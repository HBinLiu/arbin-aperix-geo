"""Tests for topic cluster QA and profile lexicon parsing."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import (
    normalize_niche_profile,
    parse_candidate_queries,
    parse_topic_clusters,
    search_queries_list,
)
from aperix_geo.services.setup.topic_qa import validate_topic_clusters


def _seed(text: str, *, dimension: str = "scenario_fit") -> dict[str, str]:
    return {
        "text": text,
        "intent": "commercial",
        "funnel": "mofu",
        "decision_type": dimension,
    }


def _cluster(name: str, seeds: list[dict[str, str]]) -> dict:
    return {
        "name": name,
        "seed_queries": seeds,
    }


def test_normalize_profile_splits_lexicon_and_search_queries() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "高端绿茶",
            "features": ["礼盒茶"],
            "customers": "企业采购",
            "topic_lexicon": {
                "category_terms": ["高端绿茶", "明前绿茶"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": ["高端绿茶商务送礼", "明前绿茶礼盒采购"],
        },
        entity="竹叶青",
    )
    assert "商务送礼" in profile["scenario_terms"]
    assert search_queries_list(profile)[0].startswith("高端绿茶")


def test_parse_topic_clusters_from_llm_payload() -> None:
    clusters = parse_topic_clusters(
        {
            "topic_clusters": [
                _cluster(
                    "商务送礼选茶",
                    [_seed("商务场合送什么茶叶合适", dimension="scenario_fit")] * 3,
                )
            ]
        }
    )
    assert clusters[0]["name"] == "商务送礼选茶"
    assert len(clusters[0]["seed_queries"]) == 3


def test_validate_topic_clusters_accepts_five_business_topics() -> None:
    clusters = parse_topic_clusters(
        {
            "topic_clusters": [
                _cluster("商务送礼选茶", [_seed("商务场合送什么茶叶合适")] * 3),
                _cluster("明前高端绿茶", [_seed("明前绿茶有哪些类型", dimension="category_awareness")] * 3),
                _cluster("企业礼盒茶", [_seed("企业采购茶叶礼盒", dimension="scenario_fit")] * 3),
                _cluster("家庭日常绿茶", [_seed("家里喝什么绿茶", dimension="scenario_fit")] * 3),
                _cluster("茶叶保存绿茶", [_seed("高档绿茶怎么保存", dimension="trust_risk")] * 3),
            ]
        }
    )
    validate_topic_clusters(
        clusters,
        industry="高端绿茶",
        lexicon_terms=["商务送礼", "明前绿茶", "礼盒茶"],
    )


def test_validate_rejects_dimension_flavored_names() -> None:
    clusters = parse_topic_clusters(
        {
            "topic_clusters": [
                _cluster("明前绿茶认知", [_seed("明前绿茶有哪些类型", dimension="category_awareness")] * 3),
                _cluster("商务送礼选茶", [_seed("商务场合送什么茶叶合适")] * 3),
                _cluster("礼盒茶对比", [_seed("高端绿茶礼盒怎么对比", dimension="solution_comparison")] * 3),
                _cluster("明前绿茶价格", [_seed("商务送礼明前绿茶一般什么价位", dimension="price_value")] * 3),
                _cluster("绿茶保存真伪", [_seed("高档绿茶怎么辨别真伪", dimension="trust_risk")] * 3),
            ]
        }
    )
    with pytest.raises(ValueError, match="决策维度"):
        validate_topic_clusters(
            clusters,
            industry="高端绿茶",
            lexicon_terms=["商务送礼", "明前绿茶", "礼盒茶"],
        )


def test_validate_rejects_generic_topic_name() -> None:
    clusters = parse_topic_clusters(
        {
            "topic_clusters": [
                _cluster("竞品对比", [_seed("跨境收款平台怎么对比", dimension="solution_comparison")] * 3),
                _cluster("跨境收款认知", [_seed("跨境收款平台有哪些类型", dimension="category_awareness")] * 3),
                _cluster("SMB收款场景", [_seed("SMB跨境收款平台怎么选", dimension="scenario_fit")] * 3),
                _cluster("跨境收款价格", [_seed("跨境收款平台月费大概多少", dimension="price_value")] * 3),
                _cluster("跨境收款合规", [_seed("跨境收款平台合规要注意什么", dimension="trust_risk")] * 3),
            ]
        }
    )
    with pytest.raises(ValueError, match="空泛"):
        validate_topic_clusters(clusters, industry="跨境支付", lexicon_terms=["跨境收款"])


def test_validate_rejects_generic_topic_when_industry_unknown() -> None:
    clusters = parse_topic_clusters(
        {
            "topic_clusters": [
                _cluster("竞品对比", [_seed("跨境收款平台怎么对比", dimension="solution_comparison")] * 3),
                _cluster("跨境收款认知", [_seed("跨境收款平台有哪些类型", dimension="category_awareness")] * 3),
                _cluster("SMB收款场景", [_seed("SMB跨境收款平台怎么选", dimension="scenario_fit")] * 3),
                _cluster("跨境收款价格", [_seed("跨境收款平台月费大概多少", dimension="price_value")] * 3),
                _cluster("跨境收款合规", [_seed("跨境收款平台合规要注意什么", dimension="trust_risk")] * 3),
            ]
        }
    )
    with pytest.raises(ValueError, match="空泛"):
        validate_topic_clusters(clusters, industry="未知行业", lexicon_terms=["跨境收款"])


def test_parse_candidate_queries() -> None:
    rows = parse_candidate_queries(
        {
            "candidate_queries": [
                {
                    "text": "SMB跨境收款平台怎么选",
                    "intent": "commercial",
                    "funnel": "mofu",
                    "decision_type": "solution_comparison",
                    "seed_terms": ["跨境收款", "SMB"],
                }
            ]
        }
    )
    assert rows[0]["text"] == "SMB跨境收款平台怎么选"
    assert rows[0]["seed_terms"] == ["跨境收款", "SMB"]
