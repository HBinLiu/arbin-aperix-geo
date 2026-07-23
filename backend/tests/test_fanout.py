"""Unit tests for query fan-out helpers and aggregation."""

from __future__ import annotations

from types import SimpleNamespace

from aperix_geo.services.providers._helpers import dedupe_search_queries, expand_search_queries
from aperix_geo.services.sampling.fanout import (
    aggregate_fanout_metrics,
    build_search_query_events,
    monitored_origin_keys,
    normalize_fanout_query_key,
    platform_exposes_search_queries,
    search_queries_from_parsed,
)


def test_normalize_fanout_query_key_folds_space_and_latin() -> None:
    assert normalize_fanout_query_key("  Foo\u3000Bar ") == "foo bar"
    assert normalize_fanout_query_key("跨境支付") == "跨境支付"


def test_expand_search_queries_splits_semicolons() -> None:
    assert expand_search_queries(
        ["高端茶客选择乌龙茶更注重香气还是回甘;高端茶客乌龙茶选择偏好 香气还是回甘"]
    ) == [
        "高端茶客选择乌龙茶更注重香气还是回甘",
        "高端茶客乌龙茶选择偏好 香气还是回甘",
    ]
    assert expand_search_queries(["a；b; c"]) == ["a", "b", "c"]
    assert expand_search_queries(["单独一条"]) == ["单独一条"]


def test_expand_search_queries_splits_common_delimiters() -> None:
    assert expand_search_queries(["甲|乙｜丙"]) == ["甲", "乙", "丙"]
    assert expand_search_queries(["甲\n乙\r\n丙"]) == ["甲", "乙", "丙"]
    assert expand_search_queries(["甲，乙,丙、丁"]) == ["甲", "乙", "丙", "丁"]
    assert expand_search_queries(["甲 / 乙"]) == ["甲", "乙"]
    # bare slash inside tokens stays intact
    assert expand_search_queries(["ChatGPT/Perplexity SEO"]) == ["ChatGPT/Perplexity SEO"]


def test_dedupe_search_queries_expands_then_dedupes() -> None:
    assert dedupe_search_queries(["a;b", "b", "a"]) == ("a", "b")


def test_search_queries_from_parsed_expands() -> None:
    assert search_queries_from_parsed(
        {"search_queries_from_api": ["foo;bar", "baz"]}
    ) == ["foo", "bar", "baz"]


def test_platform_exposes_search_queries() -> None:
    assert platform_exposes_search_queries("doubao") is True
    assert platform_exposes_search_queries("kimi") is True
    assert platform_exposes_search_queries("deepseek") is True
    assert platform_exposes_search_queries("qianwen") is False


def test_build_search_query_events() -> None:
    events = build_search_query_events(["a", "b"], platform="doubao")
    assert events == [
        {"query": "a", "platform": "doubao", "rank": 1},
        {"query": "b", "platform": "doubao", "rank": 2},
    ]


def test_aggregate_fanout_metrics_and_unmonitored() -> None:
    metrics = aggregate_fanout_metrics(
        response_query_rows=[
            ("doubao", ["跨境支付工具", "适合中小企业的收款方案"]),
            ("kimi", ["跨境支付工具", "汇率换算"]),
            ("qianwen", []),
        ],
        monitored_query_keys={normalize_fanout_query_key("汇率换算")},
        top_n=5,
    )
    assert metrics["fanout_count"] == 3
    assert metrics["fanout_avg_per_response"] == 2.0
    assert metrics["top_queries"][0]["query"] == "跨境支付工具"
    assert metrics["top_queries"][0]["frequency"] == 2
    assert "doubao" in metrics["top_queries"][0]["platforms"]
    unmonitored_queries = {item["query"] for item in metrics["unmonitored_queries"]}
    assert "跨境支付工具" in unmonitored_queries
    assert "汇率换算" not in unmonitored_queries


def test_monitored_origin_keys() -> None:
    prompts = [
        SimpleNamespace(kind="fanout", origin_query="跨境支付工具", text="跨境支付工具"),
        SimpleNamespace(kind="root", origin_query="", text="母提示词"),
    ]
    keys = monitored_origin_keys(prompts)
    assert normalize_fanout_query_key("跨境支付工具") in keys
