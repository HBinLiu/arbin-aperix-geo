"""Tests for setup prompt generation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from aperix_geo.services.prompts.setup import (
    PROMPTS_PER_TOPIC,
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
                    for i in range(PROMPTS_PER_TOPIC)
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="example.com",
        topics=["跨境支付"],
        industry="金融科技",
        core_features="API",
        target_customers="出海企业",
    )
    assert len(rows) == 1
    assert rows[0]["topic"] == "跨境支付"
    assert len(rows[0]["prompts"]) == PROMPTS_PER_TOPIC
    assert rows[0]["prompts"][0]["text"] == "问句0"
    assert rows[0]["prompts"][0]["funnel_stage"] == "tofu"
    assert rows[0]["prompts"][0]["search_intent"] == "informational"


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_accepts_legacy_string_prompts(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": ["问句A", "问句B"],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(entity="Acme", topics=["跨境支付"])
    assert rows[0]["prompts"][0]["funnel_stage"] == "mofu"
    assert rows[0]["prompts"][0]["search_intent"] == "commercial"


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
