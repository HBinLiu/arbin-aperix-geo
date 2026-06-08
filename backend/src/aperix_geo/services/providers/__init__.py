"""OpenAI-compatible chat completion client."""

from __future__ import annotations

from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.providers.errors import LLMProviderError
from aperix_geo.services.providers.openai import openai_chat_completion


__all__ = ["LLMProviderError", "chat_completion"]


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> tuple[str, dict[str, Any], int]:
    """Return (assistant_text, usage_dict, latency_ms)."""
    settings = get_settings()
    return openai_chat_completion(
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        timeout_s=settings.deepseek_chat_timeout_s,
        json_mode=json_mode,
        error_cls=LLMProviderError,
        provider_label="DeepSeek",
    )
