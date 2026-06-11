"""SearXNG-augmented chat helpers (search → inject context → LLM)."""

from __future__ import annotations

import logging
import time
from typing import Type

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.openai import openai_chat_completion
from aperix_geo.services.providers.prompts import SEARXNG_WEB_SEARCH_SYSTEM
from aperix_geo.services.searxng import SearchHit, search_text

from aperix_geo.services.providers.errors import SearxngProviderError

logger = logging.getLogger(__name__)


def last_user_content(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = (message.get("content") or "").strip()
            if content:
                return content
    return ""


def format_search_context(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        title = hit.title.strip() or "(无标题)"
        block = f"[{index}] {title}\nURL: {hit.url}"
        if hit.snippet.strip():
            block += f"\n{hit.snippet.strip()}"
        blocks.append(block)
    return "\n\n".join(blocks)


def build_messages_with_search(
    messages: list[dict[str, str]],
    *,
    hits: list[SearchHit],
    query: str,
) -> list[dict[str, str]]:
    context = format_search_context(hits)
    question = query.strip() or last_user_content(messages)
    combined_user = (
        "请结合以下联网搜索资料回答问题，并在正文中用 [1]、[2] 等角标引用来源。\n\n"
        f"## 联网搜索资料\n{context}\n\n"
        f"## 用户问题\n{question}"
    )

    system_message = {"role": "system", "content": SEARXNG_WEB_SEARCH_SYSTEM}
    if messages and messages[0].get("role") == "system":
        system_message = messages[0]

    history = [message for message in messages if message.get("role") not in {"system", "user"}]
    return [system_message, *history, {"role": "user", "content": combined_user}]


def augmented_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    provider_label: str,
    web_search: bool = True,
    searxng_max_results: int = 8,
    timeout_s: float = 120.0,
    error_cls: Type[Exception] = SearxngProviderError,
) -> SamplingChatResult:
    """Search via SearXNG, inject hits into prompt, then call chat/completions."""
    if not api_key.strip():
        raise error_cls(f"{provider_label} API key is not configured")
    if not model.strip():
        raise error_cls(f"{provider_label} model is not configured")
    if not base_url.strip():
        raise error_cls(f"{provider_label} base_url is not configured")

    query = last_user_content(messages)
    hits: list[SearchHit] = []
    chat_messages = messages
    mode = "none"

    if web_search:
        if not query:
            logger.info("%s web search skipped: empty user query", provider_label)
            mode = "searxng_skipped"
        else:
            hits = search_text(query, max_results=searxng_max_results)
            if hits:
                chat_messages = build_messages_with_search(messages, hits=hits, query=query)
                mode = "searxng"
            else:
                logger.info("%s web search returned no hits for query=%r", provider_label, query[:120])
                mode = "searxng_empty"

    t0 = time.perf_counter()
    try:
        text, usage, latency_ms = openai_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=chat_messages,
            timeout_s=timeout_s,
            error_cls=error_cls,
            provider_label=provider_label,
        )
    except Exception as exc:
        if isinstance(exc, error_cls):
            raise
        raise error_cls(str(exc)) from exc
    total_latency_ms = int((time.perf_counter() - t0) * 1000)

    source_urls = tuple(hit.url for hit in hits)
    logger.info(
        "%s SearXNG chat: mode=%s hits=%d latency_ms=%d chars=%d",
        provider_label,
        mode,
        len(hits),
        total_latency_ms,
        len(text),
    )
    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=total_latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )
