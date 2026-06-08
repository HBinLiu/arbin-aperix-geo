"""百度千帆 · 文心 ERNIE OpenAI 兼容 Chat Completions（联网搜索 web_search）。"""

from __future__ import annotations

from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.providers.errors import ErnieProviderError
from aperix_geo.services.providers.openai import (
    OpenAIWebSearchSpec,
    openai_web_search_chat,
    parse_ernie_payload,
)
from aperix_geo.services.providers.prompts import ERNIE_WEB_SEARCH_SYSTEM

ERNIE_SPEC = OpenAIWebSearchSpec(
    provider_label="Ernie",
    error_cls=ErnieProviderError,
    system_prompt=ERNIE_WEB_SEARCH_SYSTEM,
    native_mode="ernie_native",
    fallback_mode="ernie_chat",
    build_extra_body=lambda: {
        "web_search": {
            "enable": True,
            "enable_citation": True,
            "enable_trace": True,
            "search_mode": "auto",
        }
    },
    parse_payload=parse_ernie_payload,
)

parse_chat_completion_payload = parse_ernie_payload


def ernie_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    web_search: bool = True,
    timeout_s: float = 120.0,
    temperature: float = 0.3,
) -> SamplingChatResult:
    return openai_web_search_chat(
        messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        spec=ERNIE_SPEC,
        web_search=web_search,
        timeout_s=timeout_s,
        temperature=temperature,
    )
