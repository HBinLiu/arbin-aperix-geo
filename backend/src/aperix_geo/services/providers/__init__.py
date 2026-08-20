"""LLM provider helpers.

Import concrete modules (e.g. ``providers.openai``, ``providers.doubao``) directly.
This package ``__init__`` stays light so geo-web-crawl can import ``providers.doubao_web``
without installing the OpenAI SDK.
"""

from __future__ import annotations

from typing import Any

__all__ = ["LLMProviderError", "chat_completion"]


def __getattr__(name: str):
    if name == "LLMProviderError":
        from aperix_geo.services.providers.errors import LLMProviderError

        return LLMProviderError
    if name == "chat_completion":
        return chat_completion
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    json_mode: bool = False,
    timeout_s: float | None = None,
) -> tuple[str, dict[str, Any], int]:
    """Return (assistant_text, usage_dict, latency_ms)."""
    from aperix_geo.config import get_settings
    from aperix_geo.services.providers.errors import LLMProviderError
    from aperix_geo.services.providers.openai import openai_chat_completion

    settings = get_settings()
    return openai_chat_completion(
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        timeout_s=float(
            timeout_s
            if timeout_s is not None
            else settings.deepseek_chat_timeout_s
        ),
        json_mode=json_mode,
        error_cls=LLMProviderError,
        provider_label="DeepSeek",
    )
