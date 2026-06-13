"""Tests for competitor domain pre-filters and search query planning."""

from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.profile import (
    build_competitor_search_queries,
    fallback_monitoring_topics,
    monitoring_topics_from_llm,
    normalize_niche_profile,
)


def test_should_skip_media_and_aggregators() -> None:
    assert should_skip_domain("zhihu.com")
    assert should_skip_domain("36kr.com")
    assert should_skip_domain("paymentcloudinc.com")
    assert should_skip_domain("qcc.com")
    assert should_skip_domain("weibo.com")
    assert should_skip_domain("qq.com")
    assert should_skip_domain("wsjkw.hebei.gov.cn")
    assert not should_skip_domain("wise.com")
    assert not should_skip_domain("pharmasolution.com")
    assert should_skip_domain("155.cn")
    assert should_skip_domain("cr173.com")


def test_build_competitor_search_queries_intent_and_anchor() -> None:
    profile = normalize_niche_profile(
        {
            "company": "空中云汇",
            "industry": "跨境 B2B 支付",
            "core_features": ["跨境收款"],
            "target_customers": "跨境电商",
            "micro_keywords": ["SMB 跨境收款", "多币种企业钱包", "B2B 国际汇款"],
        },
        entity="airwallex.com",
    )
    queries = build_competitor_search_queries(profile, max_queries=5)
    assert queries[0] == "SMB 跨境收款"
    assert queries[1] == "多币种企业钱包"
    assert queries[2] == "B2B 国际汇款"
    assert "跨境 B2B 支付 品牌 对比" in queries


def test_build_competitor_search_queries_respects_cap() -> None:
    profile = normalize_niche_profile(
        {
            "company": "测试",
            "industry": "跨境支付",
            "micro_keywords": ["A", "B", "C", "D", "E"],
        },
        entity="test.com",
    )
    queries = build_competitor_search_queries(profile, max_queries=3)
    assert len(queries) == 3
    assert queries[0] == "A"
    assert queries[1] == "B"


def test_build_competitor_search_queries_fallback_without_keywords() -> None:
    profile = normalize_niche_profile(
        {
            "company": "测试",
            "industry": "跨境支付",
            "core_features": ["跨境收款", "多币种"],
            "target_customers": "卖家",
        },
        entity="test.com",
    )
    queries = build_competitor_search_queries(profile, max_queries=5)
    assert len(queries) >= 1
    assert "跨境支付" in queries[0]


def test_monitoring_topics_from_llm_fallback_uses_industry() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境 B2B 支付",
            "core_features": ["多币种企业钱包"],
            "target_customers": "跨境电商卖家",
            "micro_keywords": ["SMB 跨境收款 SaaS"],
        },
        entity="x.com",
    )
    topics = monitoring_topics_from_llm({}, profile)
    assert len(topics) >= 3
    assert "SMB 跨境收款 SaaS" not in topics
    assert any("跨境" in t for t in topics)
    assert any("竞品" in t for t in topics)


def test_fallback_monitoring_topics_generic_when_industry_unknown() -> None:
    profile = normalize_niche_profile({}, entity="x.com")
    topics = fallback_monitoring_topics(profile)
    assert topics == list(
        (
            "品类认知与选型",
            "核心能力与方案匹配",
            "竞品对比与替代",
            "价格与采购决策",
            "口碑与风险顾虑",
        ),
    )


def test_monitoring_topics_from_llm_filters_micro_duplicates() -> None:
    profile = normalize_niche_profile(
        {"micro_keywords": ["SMB 跨境收款 SaaS"]},
        entity="x.com",
    )
    topics = monitoring_topics_from_llm(
        {"monitoring_topics": ["SMB 跨境收款 SaaS", "跨境收款方案选型"]},
        profile,
    )
    assert topics == ["跨境收款方案选型"]


def test_monitoring_topics_from_llm_uses_llm_list() -> None:
    profile = normalize_niche_profile({}, entity="x.com")
    topics = monitoring_topics_from_llm(
        {"monitoring_topics": ["定价决策", "合规能力"]},
        profile,
    )
    assert topics == ["定价决策", "合规能力"]
