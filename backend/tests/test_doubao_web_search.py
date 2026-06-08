"""Tests for Doubao Responses API web search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.providers.doubao import (
    doubao_responses_chat,
    parse_responses_payload,
)
from aperix_geo.services.providers.prompts import DOUBAO_WEB_SEARCH_SYSTEM


def test_parse_responses_payload_extracts_text_and_citations() -> None:
    data = {
        "output": [
            {
                "type": "web_search_call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "query": "跨境支付工具",
                    "sources": [{"type": "url", "url": "https://example.com/a"}],
                },
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "推荐 A 和 B。[1] (https://example.com/a)",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://example.com/a",
                                "title": "Example A",
                            }
                        ],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
    text, source_urls, searched = parse_responses_payload(data)
    assert searched is True
    assert "推荐 A 和 B" in text
    assert source_urls == ("https://example.com/a",)


@patch("aperix_geo.services.providers.doubao.OpenAI")
def test_doubao_responses_chat_injects_system_prompt(mock_openai_cls) -> None:
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "回答正文"}],
            }
        ],
        "usage": {},
    }
    mock_response.usage = None
    mock_client = mock_openai_cls.return_value
    mock_client.responses.create.return_value = mock_response

    result = doubao_responses_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        model="doubao-seed-1-6-251015",
        web_search=True,
    )
    assert result.text == "回答正文"

    mock_openai_cls.assert_called_once_with(
        api_key="sk-test",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=120.0,
    )
    _, kwargs = mock_client.responses.create.call_args
    assert kwargs["tools"] == [{"type": "web_search"}]
    assert "include" not in kwargs
    assert kwargs["input"][0]["role"] == "system"
    assert kwargs["input"][0]["content"] == DOUBAO_WEB_SEARCH_SYSTEM
    assert kwargs["input"][1]["content"] == "问题"
