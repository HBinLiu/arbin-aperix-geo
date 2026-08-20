"""Tests for multi-provider sampling platform registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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


@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_chat_for_platform_always_uses_api_lane(mock_responses):
    """API Celery lane never embeds account crawl (even if mode is crawl_first)."""
    mock_responses.return_value = SamplingChatResult(text="api", usage={}, latency_ms=3)
    s = _settings(
        doubao_api_key="sk-b",
        doubao_sampling_mode="crawl_first",
        doubao_web_search_enabled=True,
    )
    result = chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    mock_responses.assert_called_once()


@patch("aperix_geo.services.sampling.llm.doubao_responses_chat")
def test_doubao_crawl_only_api_lane_still_calls_api(mock_responses):
    """crawl_only only applies to sampling_crawl workers; API lane stays HTTP."""
    mock_responses.return_value = SamplingChatResult(text="api", usage={}, latency_ms=3)
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_only")
    result = chat_for_platform("doubao", [{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"


def test_resolve_sampling_backend_modes():
    from aperix_geo.services.sampling.backends import resolve_sampling_backend

    assert resolve_sampling_backend("doubao", settings=_settings(doubao_sampling_mode="api_only")) == "api"
    assert resolve_sampling_backend("doubao", settings=_settings(doubao_sampling_mode="crawl_first")) == "crawl"
    assert resolve_sampling_backend("deepseek", settings=_settings(deepseek_api_key="x")) == "api"


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_pool_empty_api_fallback(mock_slot, mock_session, mock_api):
    from aperix_geo.services.sampling.crawl_capacity import CrawlPoolEmpty
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_session.return_value = MagicMock()
    mock_slot.side_effect = CrawlPoolEmpty("doubao pool empty")
    mock_api.return_value = SamplingChatResult(text="api", usage={}, latency_ms=1)
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    mock_api.assert_called_once()


@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_busy_never_api(mock_slot, mock_session):
    from aperix_geo.services.sampling.crawl_capacity import CrawlCapacityBusy
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_session.return_value = MagicMock()
    mock_slot.side_effect = CrawlCapacityBusy("doubao busy")
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    try:
        run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
        raise AssertionError("expected CrawlCapacityBusy")
    except CrawlCapacityBusy:
        pass


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_captcha_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCaptchaRequired
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_slot.return_value = MagicMock()
    mock_session.return_value = MagicMock()
    mock_crawl.side_effect = DoubaoCaptchaRequired("behavior captcha")
    mock_api.return_value = SamplingChatResult(text="api", usage={}, latency_ms=1)
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    mock_api.assert_called_once()


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_releases_slot_before_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    slot = MagicMock()
    mock_slot.return_value = slot
    mock_session.return_value = MagicMock()
    mock_crawl.side_effect = DoubaoCrawlError("page closed")

    def _api(*_a, **_k):
        slot.__exit__.assert_called_once()
        return SamplingChatResult(text="api", usage={}, latency_ms=1)

    mock_api.side_effect = _api
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    assert slot.__exit__.call_count == 1


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_unexpected_error_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_slot.return_value = MagicMock()
    mock_session.return_value = MagicMock()
    mock_crawl.side_effect = RuntimeError("spawn timeout")
    mock_api.return_value = SamplingChatResult(text="api", usage={}, latency_ms=1)
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    mock_api.assert_called_once()


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_empty_text_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_slot.return_value = MagicMock()
    mock_session.return_value = MagicMock()
    mock_crawl.return_value = SamplingChatResult(text="  ", usage={}, latency_ms=1)
    mock_api.return_value = SamplingChatResult(text="api", usage={}, latency_ms=2)
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "api"
    mock_api.assert_called_once()


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_empty_share_no_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.sampling.llm import run_doubao_account_crawl

    mock_slot.return_value = MagicMock()
    mock_session.return_value = MagicMock()
    mock_crawl.return_value = SamplingChatResult(
        text="crawl body",
        usage={},
        latency_ms=1,
        share_url="",
        search_queries=("q1",),
        source_urls=("https://example.com/a",),
    )
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    result = run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    assert result.text == "crawl body"
    assert result.share_url == ""
    assert result.search_queries == ("q1",)
    mock_api.assert_not_called()


@patch("aperix_geo.services.sampling.llm._doubao_api_chat")
@patch("aperix_geo.services.providers.doubao_web.crawler.crawl_doubao_chat")
@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.sampling.crawl_capacity.crawl_capacity_slot")
def test_run_doubao_account_crawl_share_error_no_api_fallback(
    mock_slot, mock_session, mock_crawl, mock_api
):
    from aperix_geo.services.providers.doubao_web.errors import DoubaoShareError
    from aperix_geo.services.sampling.llm import SamplingLLMError, run_doubao_account_crawl

    mock_slot.return_value = MagicMock()
    mock_session.return_value = MagicMock()
    mock_crawl.side_effect = DoubaoShareError("share button not found")
    s = _settings(doubao_api_key="sk-b", doubao_sampling_mode="crawl_first")
    with pytest.raises(SamplingLLMError, match="share button not found"):
        run_doubao_account_crawl([{"role": "user", "content": "hi"}], settings=s)
    mock_api.assert_not_called()
