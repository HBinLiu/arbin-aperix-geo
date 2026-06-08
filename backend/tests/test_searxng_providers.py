"""Tests for SearXNG-delegating sampling providers (DeepSeek / Kimi)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.providers.deepseek import deepseek_chat
from aperix_geo.services.providers.kimi import kimi_chat

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
