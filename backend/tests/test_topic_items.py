"""Tests for monitoring topic API payloads."""

from aperix_geo.services.prompts.taxonomy import normalize_decision, normalize_decision_type
from aperix_geo.services.setup.topic_items import (
    cluster_topic_names,
    clusters_for_prompt_topics,
    setup_topics_from_clusters,
    topic_name_key,
)


def test_setup_topics_from_clusters() -> None:
    items = setup_topics_from_clusters(
        [
            {"name": "商务送礼选茶"},
            {"name": "跨境 B2B 收款"},
        ]
    )
    assert items == [
        {"name": "商务送礼选茶"},
        {"name": "跨境 B2B 收款"},
    ]


def test_cluster_topic_names() -> None:
    assert cluster_topic_names(
        [
            {"name": "  A  "},
            {"name": ""},
            {"name": "B"},
        ]
    ) == ["A", "B"]


def test_topic_name_key_ignores_whitespace_and_case() -> None:
    assert topic_name_key("商务 送礼") == topic_name_key("商务送礼")
    assert topic_name_key("SMB收款") == topic_name_key("smb收款")


def test_normalize_decision_type() -> None:
    assert normalize_decision_type("price_value") == "price_value"
    assert normalize_decision_type("unknown") == "category_awareness"


def test_normalize_decision_strict() -> None:
    assert normalize_decision("price_value") == "price_value"
    assert normalize_decision("unknown") == ""


def test_clusters_for_prompt_topics_orders_by_user_topics() -> None:
    clusters = clusters_for_prompt_topics(
        ["B", "A"],
        [
            {
                "name": "A",
                "seed_queries": [
                    {
                        "text": "问句 A",
                        "intent": "commercial",
                        "funnel": "mofu",
                        "decision": "scenario_fit",
                    }
                ],
            },
            {"name": "B", "seed_queries": []},
        ],
    )
    assert [c["name"] for c in clusters] == ["B", "A"]
    assert clusters[0]["seed_queries"] == []
    assert clusters[1]["seed_queries"][0]["decision"] == "scenario_fit"
