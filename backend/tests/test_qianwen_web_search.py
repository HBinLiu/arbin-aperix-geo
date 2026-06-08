"""Tests for Qianwen DashScope Generation API web search."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from aperix_geo.services.providers.prompts import QIANWEN_WEB_SEARCH_SYSTEM
from aperix_geo.services.providers.qianwen import (
    dashscope_http_api_url,
    parse_generation_payload,
    qianwen_generation_chat,
)


def test_dashscope_http_api_url_accepts_native_base_url() -> None:
    url = dashscope_http_api_url("https://dashscope.aliyuncs.com/api/v1")
    assert url == "https://dashscope.aliyuncs.com/api/v1"


def test_dashscope_http_api_url_normalizes_legacy_compatible_base_url() -> None:
    url = dashscope_http_api_url("https://dashscope.aliyuncs.com/compatible-mode/v1")
    assert url == "https://dashscope.aliyuncs.com/api/v1"


def test_parse_generation_payload_extracts_text_and_search_results() -> None:
    data = {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "推荐 A 和 B。[ref_1]",
                    }
                }
            ],
            "search_info": {
                "search_results": [
                    {
                        "index": 1,
                        "title": "Example A",
                        "url": "https://example.com/a",
                    },
                    {
                        "index": 2,
                        "title": "Example B",
                        "url": "https://example.com/b",
                    },
                ]
            },
        },
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
    text, source_urls, searched = parse_generation_payload(data)
    assert searched is True
    assert "推荐 A 和 B" in text
    assert source_urls == ("https://example.com/a", "https://example.com/b")


@patch("aperix_geo.services.providers.qianwen.Generation.call")
def test_qianwen_generation_chat_uses_dashscope_sdk(mock_generation_call) -> None:
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.code = ""
    mock_response.message = ""
    mock_response.output = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "回答正文",
                }
            }
        ],
        "search_info": {
            "search_results": [
                {"index": 1, "title": "Source", "url": "https://example.com/source"}
            ]
        },
    }
    mock_response.usage = {}
    mock_generation_call.return_value = mock_response

    result = qianwen_generation_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        model="qwen-plus",
        web_search=True,
    )
    assert result.text == "回答正文"
    assert result.web_search_mode == "qianwen_native"
    assert result.source_urls == ("https://example.com/source",)

    mock_generation_call.assert_called_once()
    _, kwargs = mock_generation_call.call_args
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["model"] == "qwen-plus"
    assert kwargs["enable_search"] is True
    assert kwargs["result_format"] == "message"
    assert kwargs["request_timeout"] == 120.0
    assert kwargs["search_options"]["enable_source"] is True
    assert kwargs["search_options"]["enable_citation"] is True
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == QIANWEN_WEB_SEARCH_SYSTEM
    assert kwargs["messages"][1]["content"] == "问题"
