"""Kimi / Moonshot sampling · OpenAI-compatible chat with SearXNG web search."""

from __future__ import annotations

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.errors import KimiProviderError
from aperix_geo.services.providers.searxng import augmented_chat


def kimi_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    web_search: bool = True,
    searxng_max_results: int = 8,
    timeout_s: float = 180.0,
    temperature: float = 1.0,
) -> SamplingChatResult:
    return augmented_chat(
        messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        provider_label="Kimi",
        web_search=web_search,
        searxng_max_results=searxng_max_results,
        timeout_s=timeout_s,
        temperature=temperature,
        error_cls=KimiProviderError,
    )
