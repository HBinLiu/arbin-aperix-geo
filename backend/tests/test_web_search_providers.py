"""Tests for sampling provider web search integrations."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.deepseek import deepseek_chat
from aperix_geo.services.providers.doubao import (
    doubao_responses_chat,
    parse_responses_payload,
)
from aperix_geo.services.providers.ernie import (
    ernie_chat,
    parse_chat_completion_payload as parse_ernie_payload,
)
from aperix_geo.services.providers.kimi import kimi_chat
from aperix_geo.services.providers.prompts import (
    DOUBAO_WEB_SEARCH_SYSTEM,
    ERNIE_WEB_SEARCH_SYSTEM,
    QIANWEN_WEB_SEARCH_SYSTEM,
    SEARXNG_WEB_SEARCH_SYSTEM,
    YUANBAO_WEB_SEARCH_SYSTEM,
)
from aperix_geo.services.providers.qianwen import (
    dashscope_http_api_url,
    parse_generation_payload,
    qianwen_generation_chat,
)
from aperix_geo.services.providers.searxng import (
    augmented_chat,
    build_messages_with_search,
    format_search_context,
)
from aperix_geo.services.providers.yuanbao import (
    parse_chat_completion_payload as parse_yuanbao_payload,
    yuanbao_chat,
)
from aperix_geo.services.searxng import SearchHit


# --- SearXNG augmented chat ---


def test_format_search_context() -> None:
    hits = [
        SearchHit(title="Example A", url="https://example.com/a", snippet="摘要 A", query="q"),
        SearchHit(title="Example B", url="https://example.com/b", snippet="", query="q"),
    ]
    text = format_search_context(hits)
    assert "[1] Example A" in text
    assert "https://example.com/a" in text
    assert "摘要 A" in text
    assert "[2] Example B" in text


def test_build_messages_with_search_injects_system_and_context() -> None:
    hits = [SearchHit(title="Source", url="https://example.com/source", snippet="info", query="问题")]
    messages = build_messages_with_search(
        [{"role": "user", "content": "问题"}],
        hits=hits,
        query="问题",
    )
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SEARXNG_WEB_SEARCH_SYSTEM
    assert "https://example.com/source" in messages[1]["content"]
    assert "问题" in messages[1]["content"]


@patch("aperix_geo.services.providers.searxng.openai_chat_completion")
@patch("aperix_geo.services.providers.searxng.search_text")
def test_augmented_chat_returns_source_urls(mock_search, mock_chat) -> None:
    mock_search.return_value = [
        SearchHit(title="A", url="https://example.com/a", snippet="s", query="天气")
    ]
    mock_chat.return_value = ("回答正文", {}, 12)

    result = augmented_chat(
        [{"role": "user", "content": "今天天气如何？"}],
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        provider_label="DeepSeek",
        web_search=True,
        searxng_max_results=8,
    )
    assert result.text == "回答正文"
    assert result.web_search_mode == "searxng"
    assert result.source_urls == ("https://example.com/a",)
    assert result.latency_ms >= 0

    mock_search.assert_called_once_with("今天天气如何？", max_results=8)
    chat_messages = mock_chat.call_args.kwargs["messages"]
    assert chat_messages[0]["content"] == SEARXNG_WEB_SEARCH_SYSTEM
    assert "https://example.com/a" in chat_messages[1]["content"]


@patch("aperix_geo.services.providers.searxng.openai_chat_completion")
@patch("aperix_geo.services.providers.searxng.search_text")
def test_augmented_chat_skips_search_when_disabled(mock_search, mock_chat) -> None:
    mock_chat.return_value = ("plain", {}, 5)

    result = augmented_chat(
        [{"role": "user", "content": "hi"}],
        api_key="sk-test",
        base_url="https://api.moonshot.cn/v1",
        model="moonshot-v1-8k",
        provider_label="Kimi",
        web_search=False,
    )
    assert result.web_search_mode == "none"
    assert result.source_urls == ()
    mock_search.assert_not_called()
    assert mock_chat.call_args.kwargs["messages"] == [{"role": "user", "content": "hi"}]


_SEARXNG_PROVIDERS = (
    pytest.param(
        deepseek_chat,
        "aperix_geo.services.providers.deepseek.augmented_chat",
        "DeepSeek",
        "sk-d",
        "https://api.deepseek.com",
        "deepseek-chat",
        id="deepseek",
    ),
    pytest.param(
        kimi_chat,
        "aperix_geo.services.providers.kimi.augmented_chat",
        "Kimi",
        "sk-k",
        "https://api.moonshot.cn/v1",
        "moonshot-v1-8k",
        id="kimi",
    ),
)


@pytest.mark.parametrize(
    ("chat_fn", "patch_target", "provider_label", "api_key", "base_url", "model"),
    _SEARXNG_PROVIDERS,
)
def test_searxng_provider_delegates_to_augmented_chat(
    chat_fn,
    patch_target: str,
    provider_label: str,
    api_key: str,
    base_url: str,
    model: str,
) -> None:
    with patch(patch_target) as mock_augmented:
        mock_augmented.return_value = SamplingChatResult(
            text="ok",
            usage={},
            latency_ms=1,
            source_urls=("https://example.com",),
            web_search_mode="searxng",
        )

        result = chat_fn(
            [{"role": "user", "content": "hi"}],
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        assert result.text == "ok"
        mock_augmented.assert_called_once()
        kwargs = mock_augmented.call_args.kwargs
        assert kwargs["provider_label"] == provider_label
        assert kwargs["model"] == model
        if provider_label == "Kimi":
            assert kwargs["temperature"] == 1.0


# --- Doubao ---


def test_doubao_parse_responses_payload_extracts_text_and_citations() -> None:
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


# --- Ernie ---


def test_ernie_parse_chat_completion_payload_extracts_text_and_search_results() -> None:
    response = {
        "choices": [{"message": {"role": "assistant", "content": "推荐 A 和 B。^[1]^"}}],
        "search_results": [
            {"index": 1, "title": "Example A", "url": "https://example.com/a"},
            {"index": 2, "title": "Example B", "url": "https://example.com/b"},
        ],
    }
    text, source_urls, searched = parse_ernie_payload(response)
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


# --- Yuanbao ---


def test_yuanbao_parse_chat_completion_payload_extracts_text_and_search_results() -> None:
    response = {
        "choices": [{"message": {"role": "assistant", "content": "推荐 A 和 B。[1]"}}],
        "search_info": {
            "search_results": [
                {"index": 1, "title": "Example A", "url": "https://example.com/a"},
                {"index": 2, "title": "Example B", "url": "https://example.com/b"},
            ]
        },
    }
    text, source_urls, searched = parse_yuanbao_payload(response)
    assert searched is True
    assert "推荐 A 和 B" in text
    assert source_urls == ("https://example.com/a", "https://example.com/b")


def test_yuanbao_parse_chat_completion_payload_supports_pascal_case_search_info() -> None:
    response = {
        "choices": [{"message": {"role": "assistant", "content": "正文"}}],
        "SearchInfo": {
            "SearchResults": [
                {"Index": 1, "Title": "Example", "Url": "https://example.com/pascal"},
            ]
        },
    }
    _, source_urls, searched = parse_yuanbao_payload(response)
    assert searched is True
    assert source_urls == ("https://example.com/pascal",)


@patch("aperix_geo.services.providers.openai.OpenAI")
def test_yuanbao_chat_injects_web_search_extra_body(mock_openai_cls) -> None:
    mock_message = MagicMock()
    mock_message.content = "回答正文"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_response.model_dump.return_value = {
        "choices": [{"message": {"content": "回答正文"}}],
        "search_info": {
            "search_results": [
                {"index": 1, "title": "Source", "url": "https://example.com/source"}
            ]
        },
    }
    mock_client = mock_openai_cls.return_value
    mock_client.chat.completions.create.return_value = mock_response

    result = yuanbao_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://api.hunyuan.cloud.tencent.com/v1",
        model="hunyuan-turbos-latest",
        web_search=True,
    )
    assert result.text == "回答正文"
    assert result.web_search_mode == "yuanbao_native"
    assert result.source_urls == ("https://example.com/source",)

    mock_openai_cls.assert_called_once_with(
        api_key="sk-test",
        base_url="https://api.hunyuan.cloud.tencent.com/v1",
        timeout=120.0,
    )
    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["extra_body"] == {
        "enable_enhancement": True,
        "search_info": True,
        "citation": True,
    }
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == YUANBAO_WEB_SEARCH_SYSTEM
    assert kwargs["messages"][1]["content"] == "问题"


# --- Qianwen ---


def test_dashscope_http_api_url_accepts_native_base_url() -> None:
    url = dashscope_http_api_url("https://dashscope.aliyuncs.com/api/v1")
    assert url == "https://dashscope.aliyuncs.com/api/v1"


def test_dashscope_http_api_url_normalizes_legacy_compatible_base_url() -> None:
    url = dashscope_http_api_url("https://dashscope.aliyuncs.com/compatible-mode/v1")
    assert url == "https://dashscope.aliyuncs.com/api/v1"


def test_qianwen_parse_generation_payload_extracts_text_and_search_results() -> None:
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
