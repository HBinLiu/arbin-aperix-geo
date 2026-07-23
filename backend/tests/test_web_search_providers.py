"""Tests for sampling provider web search integrations."""

from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import get_settings
from aperix_geo.services.providers.deepseek import (
    build_web_search_tool,
    deepseek_chat,
    normalize_web_search_tool_type,
    parse_deepseek_anthropic_payload,
    resolve_deepseek_anthropic_base_url,
)
from aperix_geo.services.providers.errors import DeepseekProviderError
from aperix_geo.services.providers.doubao import (
    doubao_responses_chat,
    parse_responses_payload,
)
from aperix_geo.services.providers.ernie import (
    ernie_chat,
    parse_chat_completion_payload as parse_ernie_payload,
)
from aperix_geo.services.providers.kimi import kimi_chat, parse_kimi_payload
from aperix_geo.services.providers.prompts import (
    DEEPSEEK_WEB_SEARCH_SYSTEM,
    DOUBAO_WEB_SEARCH_SYSTEM,
    ERNIE_WEB_SEARCH_SYSTEM,
    KIMI_WEB_SEARCH_SYSTEM,
    QIANWEN_WEB_SEARCH_SYSTEM,
    YUANBAO_WEB_SEARCH_SYSTEM,
)
from aperix_geo.services.providers.qianwen import (
    dashscope_http_api_url,
    parse_generation_payload,
    qianwen_generation_chat,
)
from aperix_geo.services.providers.yuanbao import (
    parse_chat_completion_payload as parse_yuanbao_payload,
    yuanbao_chat,
)


# --- DeepSeek ---


def test_resolve_deepseek_anthropic_base_url() -> None:
    assert (
        resolve_deepseek_anthropic_base_url("https://api.deepseek.com")
        == "https://api.deepseek.com/anthropic"
    )
    assert (
        resolve_deepseek_anthropic_base_url("https://api.deepseek.com/v1")
        == "https://api.deepseek.com/anthropic"
    )
    assert (
        resolve_deepseek_anthropic_base_url(
            "https://api.deepseek.com",
            anthropic_base_url="https://custom.example/anthropic",
        )
        == "https://custom.example/anthropic"
    )


def test_build_web_search_tool_uses_configured_type() -> None:
    tool = build_web_search_tool(tool_type="web_search_20260209", max_uses=3)
    assert tool == {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
    }


def test_normalize_web_search_tool_type_rejects_unknown() -> None:
    with pytest.raises(DeepseekProviderError, match="unsupported web_search tool type"):
        normalize_web_search_tool_type("web_search_20990101")


def test_deepseek_parse_anthropic_payload_extracts_text_and_urls() -> None:
    data = {
        "content": [
            {"type": "server_tool_use", "name": "web_search", "id": "srv_1", "input": {"query": "DeepSeek 文档"}},
            {
                "type": "web_search_tool_result",
                "tool_use_id": "srv_1",
                "content": [
                    {
                        "type": "web_search_result",
                        "url": "https://docs.deepseek.com/guide",
                        "title": "Guide",
                    }
                ],
            },
            {
                "type": "text",
                "text": "DeepSeek 提供 Context Caching。[1]",
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "url": "https://docs.deepseek.com/guide",
                        "title": "Guide",
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 100, "output_tokens": 50, "server_tool_use": {"web_search_requests": 1}},
    }
    text, source_urls, searched, search_queries = parse_deepseek_anthropic_payload(data)
    assert searched is True
    assert "DeepSeek 提供 Context Caching" in text
    assert "https://docs.deepseek.com/guide" in source_urls
    assert search_queries == ("DeepSeek 文档",)


@patch("aperix_geo.services.providers.deepseek.httpx.Client")
def test_deepseek_chat_uses_anthropic_web_search(mock_client_cls) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [
            {
                "type": "web_search_tool_result",
                "content": [
                    {
                        "type": "web_search_result",
                        "url": "https://docs.deepseek.com/guide",
                        "title": "Guide",
                    }
                ],
            },
            {"type": "text", "text": "回答正文"},
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5, "server_tool_use": {"web_search_requests": 1}},
    }
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.post.return_value = mock_response

    result = deepseek_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-pro",
        web_search=True,
    )
    assert result.text == "回答正文"
    assert result.web_search_mode == "deepseek_native"
    assert "https://docs.deepseek.com/guide" in result.source_urls

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args.args[0] == "https://api.deepseek.com/anthropic/v1/messages"
    body = call_args.kwargs["json"]
    assert body["tools"] == [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
    ]
    assert body["system"] == DEEPSEEK_WEB_SEARCH_SYSTEM
    assert body["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "问题"}]}
    ]


@patch("aperix_geo.services.providers.deepseek.openai_chat_completion")
def test_deepseek_chat_skips_web_search_when_disabled(mock_chat) -> None:
    mock_chat.return_value = ("plain", {}, 5)

    result = deepseek_chat(
        [{"role": "user", "content": "hi"}],
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-pro",
        web_search=False,
    )
    assert result.web_search_mode == "none"
    assert result.source_urls == ()
    mock_chat.assert_called_once()
    assert mock_chat.call_args.kwargs["messages"] == [{"role": "user", "content": "hi"}]


# --- Kimi ---


def test_kimi_parse_payload_extracts_text_and_urls() -> None:
    text, source_urls, searched = parse_kimi_payload(
        "推荐 A 和 B。[1](https://docs.moonshot.cn/a)",
        searched=True,
        tool_source_urls=["https://docs.moonshot.cn/b"],
    )
    assert searched is True
    assert "推荐 A 和 B" in text
    assert "https://docs.moonshot.cn/a" in source_urls
    assert "https://docs.moonshot.cn/b" in source_urls


@patch("aperix_geo.services.providers.kimi.OpenAI")
def test_kimi_chat_runs_web_search_tool_loop(mock_openai_cls) -> None:
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "$web_search"
    tool_call.function.arguments = json.dumps(
        {
            "query": "跨境支付工具对比",
            "search_result": [{"url": "https://docs.moonshot.cn/source"}],
        }
    )

    tool_message = MagicMock()
    tool_message.content = None
    tool_message.tool_calls = [tool_call]
    tool_choice = MagicMock()
    tool_choice.finish_reason = "tool_calls"
    tool_choice.message = tool_message

    final_message = MagicMock()
    final_message.content = "回答正文 [1](https://docs.moonshot.cn/source)"
    final_message.tool_calls = None
    final_choice = MagicMock()
    final_choice.finish_reason = "stop"
    final_choice.message = final_message

    tool_response = MagicMock()
    tool_response.choices = [tool_choice]
    tool_response.usage = MagicMock()
    tool_response.usage.model_dump.return_value = {
        "prompt_tokens": 100,
        "completion_tokens": 0,
        "total_tokens": 100,
    }

    final_response = MagicMock()
    final_response.choices = [final_choice]
    final_response.usage = MagicMock()
    final_response.usage.model_dump.return_value = {
        "prompt_tokens": 200,
        "completion_tokens": 50,
        "total_tokens": 250,
    }

    mock_client = mock_openai_cls.return_value
    mock_client.chat.completions.create.side_effect = [tool_response, final_response]
    tool_message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "$web_search", "arguments": tool_call.function.arguments},
            }
        ],
    }

    result = kimi_chat(
        [{"role": "user", "content": "问题"}],
        api_key="sk-test",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k2.6",
        web_search=True,
    )
    assert result.text == "回答正文 [1](https://docs.moonshot.cn/source)"
    assert result.web_search_mode == "kimi_native"
    assert "https://docs.moonshot.cn/source" in result.source_urls
    assert result.search_queries == ("跨境支付工具对比",)
    assert mock_client.chat.completions.create.call_count == 2

    first_kwargs = mock_client.chat.completions.create.call_args_list[0].kwargs
    assert first_kwargs["tools"] == [
        {"type": "builtin_function", "function": {"name": "$web_search"}}
    ]
    assert first_kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert first_kwargs["messages"][0]["content"] == KIMI_WEB_SEARCH_SYSTEM


@patch("aperix_geo.services.providers.kimi.openai_chat_completion")
def test_kimi_chat_skips_web_search_when_disabled(mock_chat) -> None:
    mock_chat.return_value = ("plain", {}, 5)

    result = kimi_chat(
        [{"role": "user", "content": "hi"}],
        api_key="sk-test",
        base_url="https://api.moonshot.cn/v1",
        model="moonshot-v1-8k",
        web_search=False,
    )
    assert result.web_search_mode == "none"
    assert result.source_urls == ()
    mock_chat.assert_called_once()
    assert mock_chat.call_args.kwargs["messages"] == [{"role": "user", "content": "hi"}]


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
    text, source_urls, searched, search_queries = parse_responses_payload(data)
    assert searched is True
    assert "推荐 A 和 B" in text
    assert source_urls == ("https://example.com/a",)
    assert search_queries == ("跨境支付工具",)


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
        max_retries=0,
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
        max_retries=0,
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


# --- Live integration (requires API keys; run with: pytest -m live -v -s) ---


def _kimi_live_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.kimi_api_key.strip()
        and settings.kimi_model.strip()
        and settings.kimi_base_url.strip()
    )


def _deepseek_live_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.deepseek_api_key.strip()
        and settings.deepseek_model.strip()
        and settings.deepseek_base_url.strip()
    )


@pytest.mark.live
@pytest.mark.skipif(
    not _kimi_live_configured(),
    reason="KIMI_API_KEY / KIMI_MODEL / KIMI_BASE_URL not configured",
)
def test_kimi_web_search_live() -> None:
    """验证 Kimi 官方 $web_search 能完成一次联网问答。"""
    settings = get_settings()
    result = kimi_chat(
        [
            {
                "role": "user",
                "content": (
                    "请联网搜索 Moonshot AI 的 Context Caching 技术，"
                    "用两三句话说明它是什么，并在文末列出参考链接。"
                ),
            }
        ],
        api_key=settings.kimi_api_key,
        base_url=settings.kimi_base_url,
        model=settings.kimi_model,
        web_search=True,
        web_search_max_uses=settings.kimi_web_search_max_uses,
        timeout_s=settings.kimi_chat_timeout_s,
        temperature=settings.kimi_temperature,
    )

    assert result.text.strip(), "Kimi returned empty text"
    assert result.web_search_mode == "kimi_native", (
        f"expected $web_search tool call, got mode={result.web_search_mode!r}"
    )
    assert result.latency_ms > 0
    assert result.usage.get("total_tokens", 0) > 0 or result.usage.get("completion_tokens", 0) > 0

    has_citations = bool(result.source_urls) or "http" in result.text.lower()
    assert has_citations, "expected source URLs or http links in response"

    print(
        f"\n[kimi live] mode={result.web_search_mode} "
        f"latency_ms={result.latency_ms} "
        f"source_urls={len(result.source_urls)} "
        f"chars={len(result.text)}"
    )
    print(f"[kimi live] preview: {result.text[:400]}{'…' if len(result.text) > 400 else ''}")


@pytest.mark.live
@pytest.mark.skipif(
    not _deepseek_live_configured(),
    reason="DEEPSEEK_API_KEY / DEEPSEEK_MODEL / DEEPSEEK_BASE_URL not configured",
)
def test_deepseek_web_search_live() -> None:
    """验证 DeepSeek Anthropic 原生 web_search 能完成一次联网问答。"""
    settings = get_settings()
    result = deepseek_chat(
        [
            {
                "role": "user",
                "content": (
                    "请联网搜索 DeepSeek API 的 Context Caching 功能，"
                    "用两三句话说明它是什么，并在文末列出参考链接。"
                ),
            }
        ],
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        anthropic_base_url=settings.deepseek_anthropic_base_url,
        web_search=True,
        web_search_tool_type=settings.deepseek_web_search_tool_type,
        web_search_max_uses=settings.deepseek_web_search_max_uses,
        timeout_s=settings.deepseek_chat_timeout_s,
    )

    assert result.text.strip(), "DeepSeek returned empty text"
    assert result.web_search_mode == "deepseek_native", (
        f"expected native web search, got mode={result.web_search_mode!r}"
    )
    assert result.latency_ms > 0
    assert result.usage.get("total_tokens", 0) > 0 or result.usage.get("completion_tokens", 0) > 0

    has_citations = bool(result.source_urls) or "http" in result.text.lower()
    assert has_citations, "expected source URLs or http links in response"

    print(
        f"\n[deepseek live] mode={result.web_search_mode} "
        f"latency_ms={result.latency_ms} "
        f"source_urls={len(result.source_urls)} "
        f"chars={len(result.text)}"
    )
    print(f"[deepseek live] preview: {result.text[:400]}{'…' if len(result.text) > 400 else ''}")
