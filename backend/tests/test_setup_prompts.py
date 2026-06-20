"""Tests for setup prompt generation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from aperix_geo.services.prompts.setup import (
    PROMPT_PER_TOPIC,
    generate_setup_prompts,
)


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_llm(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": [
                    {
                        "text": f"问句{i}",
                        "funnel": "mofu" if i % 2 else "tofu",
                        "intent": "commercial" if i % 2 else "informational",
                    }
                    for i in range(PROMPT_PER_TOPIC)
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="example.com",
        topics=["跨境支付"],
        industry="金融科技",
        features="API",
        customers="出海企业",
    )
    assert len(rows) == 1
    assert rows[0]["topic"] == "跨境支付"
    assert len(rows[0]["prompts"]) == PROMPT_PER_TOPIC
    assert rows[0]["prompts"][0]["text"] == "问句0"
    assert rows[0]["prompts"][0]["funnel_stage"] == "tofu"
    assert rows[0]["prompts"][0]["search_intent"] == "informational"


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_passes_exclude_prompts(mock_chat) -> None:
    payload = {"topics": [{"topic": "支付", "prompts": [{"text": "问句A", "funnel": "tofu", "intent": "informational"}]}]}
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    generate_setup_prompts(
        entity="Acme",
        topics=["支付"],
        exclude_prompts=["已有问题", "  "],
    )

    user_content = mock_chat.call_args[0][0][1]["content"]
    assert '"exclude_prompts": [\n    "已有问题"\n  ]' in user_content
    assert "region" not in user_content
    assert "language" not in user_content


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_raises_on_llm_error(mock_chat) -> None:
    mock_chat.side_effect = ValueError("missing topics array")

    with pytest.raises(ValueError):
        generate_setup_prompts(entity="Acme", topics=["支付"])


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_filters_excluded_text(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "支付",
                "prompts": [
                    {"text": "已有问题", "funnel": "tofu", "intent": "informational"},
                    {"text": "新问题", "funnel": "mofu", "intent": "commercial"},
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["支付"],
        prompts_per_topic=2,
        exclude_prompts=["已有问题"],
    )
    texts = [p["text"] for p in rows[0]["prompts"]]
    assert "已有问题" not in texts
    assert "新问题" in texts


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_exact_topic_match_only(mock_chat) -> None:
    batch = {
        "topics": [
            {
                "topic": "AI 搜索可见度",
                "prompts": [{"text": "问句A", "funnel": "tofu", "intent": "informational"}],
            }
        ]
    }
    retry = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": [{"text": "问句B", "funnel": "mofu", "intent": "commercial"}],
            }
        ]
    }
    mock_chat.side_effect = [
        (json.dumps(batch), "deepseek", 100.0),
        (json.dumps(retry), "deepseek", 50.0),
    ]

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["AI 搜索可见度", "跨境支付"],
        prompts_per_topic=1,
    )
    by_topic = {row["topic"]: row["prompts"][0]["text"] for row in rows}
    assert by_topic["AI 搜索可见度"] == "问句A"
    assert by_topic["跨境支付"] == "问句B"
    assert mock_chat.call_count == 2


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_raises_when_topic_still_empty(mock_chat) -> None:
    mock_chat.return_value = (json.dumps({"topics": []}), "deepseek", 100.0)

    with pytest.raises(ValueError, match="未生成有效问句"):
        generate_setup_prompts(entity="Acme", topics=["支付"], prompts_per_topic=1)
