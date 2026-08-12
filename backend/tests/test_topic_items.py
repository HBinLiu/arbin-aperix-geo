"""Tests for monitoring topic API payloads."""

from aperix_geo.services.prompts.taxonomy import normalize_decision, normalize_decision_type
from aperix_geo.services.setup.topic_items import (
    normalize_topic_names,
    setup_topics_from_names,
    topic_name_key,
)


def test_setup_topics_from_names() -> None:
    items = setup_topics_from_names(["商务送礼选茶", "跨境 B2B 收款"])
    assert items == [
        {"name": "商务送礼选茶"},
        {"name": "跨境 B2B 收款"},
    ]


def test_normalize_topic_names() -> None:
    assert normalize_topic_names(
        [
            {"name": "  A  "},
            {"name": ""},
            {"name": "B"},
            "A",
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
