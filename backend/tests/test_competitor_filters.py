"""Tests for competitor domain pre-filters and search query planning."""

from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.profile import build_search_queries, plan_micro_keyword_queries


def _keywords_in_queries(keywords: list[str], queries: list[str]) -> set[str]:
    found: set[str] = set()
    for q in queries:
        tokens = q.split()
        for kw in keywords:
            if kw in tokens:
                found.add(kw)
    return found


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


def test_plan_one_keyword_per_round_when_topics_le_rounds() -> None:
    keywords = ["A", "B", "C"]
    assert plan_micro_keyword_queries(keywords, max_rounds=5) == ["A", "B", "C"]


def test_plan_one_keyword_per_round_when_equal() -> None:
    keywords = ["A", "B", "C", "D", "E"]
    assert plan_micro_keyword_queries(keywords, max_rounds=5) == keywords


def test_plan_packs_all_topics_when_topics_gt_rounds() -> None:
    keywords = ["A", "B", "C", "D", "E"]
    queries = plan_micro_keyword_queries(keywords, max_rounds=3)
    assert queries == ["A B", "C D", "E"]
    assert _keywords_in_queries(keywords, queries) == set(keywords)


def test_plan_packs_evenly_for_two_rounds() -> None:
    keywords = ["A", "B", "C", "D", "E"]
    queries = plan_micro_keyword_queries(keywords, max_rounds=2)
    assert queries == ["A B C", "D E"]
    assert _keywords_in_queries(keywords, queries) == set(keywords)


def test_plan_deduplicates_keywords() -> None:
    queries = plan_micro_keyword_queries(["A", "A", "B"], max_rounds=2)
    assert queries == ["A", "B"]


def test_build_search_queries_one_per_keyword() -> None:
    profile = {
        "company": "测试",
        "industry": "跨境支付",
        "core_features": "",
        "target_customers": "",
        "micro_keywords": "跨境收款、多币种账户、B2B支付、企业钱包、国际汇款",
    }
    queries = build_search_queries(profile, max_queries=5)
    assert queries == ["跨境收款", "多币种账户", "B2B支付", "企业钱包", "国际汇款"]


def test_build_search_queries_uses_all_topics_within_round_limit() -> None:
    profile = {
        "company": "测试",
        "industry": "跨境支付",
        "core_features": "",
        "target_customers": "",
        "micro_keywords": "A、B、C、D、E",
    }
    keywords = ["A", "B", "C", "D", "E"]
    queries = build_search_queries(profile, max_queries=3)
    assert queries == ["A B", "C D", "E"]
    assert _keywords_in_queries(keywords, queries) == set(keywords)
