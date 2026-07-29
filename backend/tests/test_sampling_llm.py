"""Tests for multi-provider sampling platform registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.config import Settings
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.llm import (
    SamplingLLMError,
    chat_for_platform,
    configured_platforms,
    list_sampling_platforms,
    llm_model_for_platform,
    prefer_default_platforms,
    resolve_sampling_platform,
)


def _settings(**overrides) -> Settings:
    base = {
        "deepseek_api_key": "",
        "yuanbao_api_key": "",
        "doubao_api_key": "",
        "qianwen_api_key": "",
        "kimi_api_key": "",
        "ernie_api_key": "",
    }
    base.update(overrides)
    return Settings(**base)


def test_list_platforms_only_configured():
    s = _settings(deepseek_api_key="sk-d", ernie_api_key="sk-e")
    platforms = list_sampling_platforms(settings=s)
    names = {p["platform"] for p in platforms}
    assert names == {"deepseek", "ernie"}


def test_configured_platforms():
    s = _settings(deepseek_api_key="sk-d", kimi_api_key="sk-k")
    assert configured_platforms(settings=s) == ["deepseek", "kimi"]


def test_preferred_default_is_doubao_when_configured():
    s = _settings(deepseek_api_key="sk-d", doubao_api_key="sk-b", kimi_api_key="sk-k")
    assert prefer_default_platforms(settings=s) == ["doubao"]


def test_preferred_default_falls_back_when_doubao_missing():
    s = _settings(deepseek_api_key="sk-d", kimi_api_key="sk-k")
    assert prefer_default_platforms(settings=s) == ["deepseek"]


def test_llm_model_for_platform():
    s = _settings(deepseek_api_key="sk-d")
    assert llm_model_for_platform("deepseek", settings=s) == s.deepseek_model


def test_resolve_unknown_platform():
    s = _settings(deepseek_api_key="sk-d")
    try:
        resolve_sampling_platform("nonexistent", settings=s)
        assert False, "expected error"
    except SamplingLLMError as e:
        assert "nonexistent" in str(e)


@patch("aperix_geo.services.sampling.llm.deepseek_chat")
def test_chat_for_platform_deepseek(mock_deepseek_chat):
    mock_deepseek_chat.return_value = SamplingChatResult(text="hello", usage={}, latency_ms=10)
    s = _settings(deepseek_api_key="sk-d")
    result = chat_for_platform("deepseek", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "hello"
    assert result.latency_ms == 10
    mock_deepseek_chat.assert_called_once()


@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_api_only_calls_responses_api(mock_responses):
    mock_responses.return_value = SamplingChatResult(
        text="api", usage={}, latency_ms=5, share_url=""
    )
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="api_only", doubao_web_search_enabled=True)
    result = chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    assert result.share_url == ""
    mock_responses.assert_called_once()


@patch("aperix_geo.services.sampling.llm.try_doubao_web_crawl", return_value=None)
@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_crawl_first_falls_back_to_api_when_crawl_missing(mock_responses, _mock_crawl):
    mock_responses.return_value = SamplingChatResult(text="fallback", usage={}, latency_ms=3)
    s = _settings(
        doubao_api_key="sk-b",
        doubao_sampling_mode="crawl_first",
        doubao_web_search_enabled=True,
    )
    result = chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "fallback"
    mock_responses.assert_called_once()


@patch("aperix_geo.services.sampling.llm.try_doubao_web_crawl", return_value=None)
@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_crawl_only_raises_when_crawl_unavailable(mock_responses, _mock_crawl):
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_only")
    try:
        chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
        assert False, "expected SamplingLLMError"
    except SamplingLLMError as exc:
        assert "crawl" in str(exc).lower()
    mock_responses.assert_not_called()


@patch("aperix_geo.services.sampling.llm.try_doubao_web_crawl")
@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_crawl_first_uses_crawl_when_available(mock_responses, mock_crawl):
    mock_crawl.return_value = SamplingChatResult(
        text="crawled",
        usage={},
        latency_ms=90,
        web_search_mode="doubao_web_crawl",
        share_url="https://www.doubao.com/share/x",
    )
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "crawled"
    assert result.share_url.startswith("https://")
    mock_responses.assert_not_called()


@patch("aperix_geo.services.providers.doubao_web.accounts.count_fresh_active_accounts", return_value=0)
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
def test_try_doubao_web_crawl_skips_without_storage_state(mock_crawl, mock_session, _mock_count):
    from aperix_geo.services.sampling.llm import try_doubao_web_crawl

    mock_session.return_value = MagicMock()
    s = _settings(doubao_api_key="sk-b", doubao_crawl_storage_state_path="")
    assert try_doubao_web_crawl([{"role": "user", "content": "hi"}], settings=s) is None
    mock_crawl.assert_not_called()
