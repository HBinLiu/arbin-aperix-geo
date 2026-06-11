"""腾讯元宝 / 混元 OpenAI 兼容 Chat Completions（联网搜索 extra_body）。"""

from __future__ import annotations

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.errors import YuanbaoProviderError
from aperix_geo.services.providers.openai import (
    OpenAIWebSearchSpec,
    openai_web_search_chat,
    parse_yuanbao_payload,
)
from aperix_geo.services.providers.prompts import YUANBAO_WEB_SEARCH_SYSTEM

YUANBAO_SPEC = OpenAIWebSearchSpec(
    provider_label="Yuanbao",
    error_cls=YuanbaoProviderError,
    system_prompt=YUANBAO_WEB_SEARCH_SYSTEM,
    native_mode="yuanbao_native",
    fallback_mode="yuanbao_chat",
    build_extra_body=lambda: {
        "enable_enhancement": True,
        "search_info": True,
        "citation": True,
    },
    parse_payload=parse_yuanbao_payload,
)

parse_chat_completion_payload = parse_yuanbao_payload


def yuanbao_chat(
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
        spec=YUANBAO_SPEC,
        web_search=web_search,
        timeout_s=timeout_s,
        temperature=temperature,
    )
