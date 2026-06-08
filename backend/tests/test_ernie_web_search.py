"""Tests for Ernie / Qianfan web search via OpenAI-compatible extra_body."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.providers.ernie import (
    parse_chat_completion_payload,
    ernie_chat,
)
from aperix_geo.services.providers.prompts import ERNIE_WEB_SEARCH_SYSTEM


def test_parse_chat_completion_payload_extracts_text_and_search_results() -> None:
    response = {
        "choices": [{"message": {"role": "assistant", "content": "推荐 A 和 B。^[1]^"}}],
        "search_results": [
            {"index": 1, "title": "Example A", "url": "https://example.com/a"},
            {"index": 2, "title": "Example B", "url": "https://example.com/b"},
        ],
    }
    text, source_urls, searched = parse_chat_completion_payload(response)
    assert searched is True
    assert "推荐 A 和 B" in text
    assert source_urls == ("https://example.com/a", "https://example.com/b")


@patch("aperix_geo.services.providers.openai.OpenAI")
def test_ernie_chat_injects_web_search_extra_body(mock_openai_cls) -> None:
    mock_message = MagicMock()
    mock_message.content = "回答正文"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_response.search_results = [
        {"index": 1, "title": "Source", "url": "https://example.com/source"}
    ]
    mock_response.model_dump.return_value = {
        "choices": [{"message": {"content": "回答正文"}}],
        "search_results": [
            {"index": 1, "title": "Source", "url": "https://example.com/source"}
        ],
    }
    mock_client = mock_openai_cls.return_value
    mock_client.chat.completions.create.return_value = mock_response

    result = ernie_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://qianfan.baidubce.com/v2",
        model="ernie-4.0-8k",
        web_search=True,
    )
    assert result.text == "回答正文"
    assert result.web_search_mode == "ernie_native"
    assert result.source_urls == ("https://example.com/source",)

    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["extra_body"] == {
        "web_search": {
            "enable": True,
            "enable_citation": True,
            "enable_trace": True,
            "search_mode": "auto",
        }
    }
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == ERNIE_WEB_SEARCH_SYSTEM
    assert kwargs["messages"][1]["content"] == "问题"
