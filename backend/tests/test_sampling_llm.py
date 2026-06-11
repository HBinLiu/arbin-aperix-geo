"""Tests for multi-provider sampling platform registry."""

from __future__ import annotations

from unittest.mock import patch

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
