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
                "prompts": [f"问句{i}" for i in range(PROMPTS_PER_TOPIC)],
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


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_raises_on_llm_error(mock_chat) -> None:
    mock_chat.side_effect = ValueError("missing topics array")

    with pytest.raises(ValueError):
        generate_setup_prompts(entity="Acme", topics=["支付"])
