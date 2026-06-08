"""Tests for SearXNG-augmented chat helpers."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.providers.prompts import SEARXNG_WEB_SEARCH_SYSTEM
from aperix_geo.services.providers.searxng import (
    augmented_chat,
    build_messages_with_search,
    format_search_context,
)
from aperix_geo.services.web_search import SearchHit


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
