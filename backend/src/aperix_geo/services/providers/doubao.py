"""Volcengine Ark · Doubao Responses API (web search)."""

from __future__ import annotations

import logging
import time
from typing import Any

from openai import APIError, APITimeoutError, OpenAI

from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.providers._helpers import dedupe_urls, response_data, with_system_prompt
from aperix_geo.services.providers.errors import DoubaoProviderError, raise_provider_error
from aperix_geo.services.providers.openai import _usage_dict, openai_chat_completion
from aperix_geo.services.providers.prompts import DOUBAO_WEB_SEARCH_SYSTEM

logger = logging.getLogger(__name__)


def _collect_citation_urls(output: list[Any]) -> list[str]:
    urls: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            action = item.get("action")
            if isinstance(action, dict):
                for src in action.get("sources") or []:
                    if isinstance(src, dict) and src.get("url"):
                        urls.append(str(src["url"]))
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            for ann in block.get("annotations") or []:
                if not isinstance(ann, dict):
                    continue
                if ann.get("type") == "url_citation" and ann.get("url"):
                    urls.append(str(ann["url"]))
    return urls


def _extract_response_text(output: list[Any]) -> str:
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()


def _web_search_used(output: list[Any]) -> bool:
    return any(isinstance(item, dict) and item.get("type") == "web_search_call" for item in output)


def parse_responses_payload(data: dict[str, Any] | Any) -> tuple[str, tuple[str, ...], bool]:
    payload = response_data(data)
    output = payload.get("output") or []
    if not isinstance(output, list):
        output = []
    text = _extract_response_text(output)
    source_urls = dedupe_urls(_collect_citation_urls(output))
    return text, source_urls, _web_search_used(output)


def doubao_responses_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    web_search: bool = True,
    timeout_s: float = 120.0,
) -> SamplingChatResult:
    """Call Ark Responses API; optionally enable built-in web_search tool."""
    if not api_key.strip():
        raise DoubaoProviderError("Doubao API key is not configured")
    if not model.strip():
        raise DoubaoProviderError("Doubao model is not configured")
    if not base_url.strip():
        raise DoubaoProviderError("Doubao base_url is not configured")

    client = OpenAI(
        api_key=api_key.strip(),
        base_url=base_url.strip(),
        timeout=timeout_s,
    )
    kwargs: dict[str, Any] = {
        "model": model.strip(),
        "input": with_system_prompt(messages, DOUBAO_WEB_SEARCH_SYSTEM),
        "stream": False,
    }
    if web_search:
        kwargs["tools"] = [{"type": "web_search"}]

    t0 = time.perf_counter()
    try:
        response = client.responses.create(**kwargs)
    except APITimeoutError as exc:
        raise_provider_error(
            DoubaoProviderError,
            f"Doubao timeout: {exc}",
            retryable=True,
            cause=exc,
        )
    except APIError as exc:
        detail = (getattr(exc, "message", None) or str(exc))[:800]
        status = getattr(exc, "status_code", None)
        if status is not None:
            raise_provider_error(
                DoubaoProviderError,
                f"Doubao HTTP {status}: {detail}",
                status_code=status,
                cause=exc,
            )
        raise_provider_error(DoubaoProviderError, f"Doubao API error: {detail}", cause=exc)
    except Exception as exc:
        raise_provider_error(DoubaoProviderError, f"Doubao error: {exc}", cause=exc)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    text, source_urls, searched = parse_responses_payload(response)
    if not text:
        raise DoubaoProviderError(f"Doubao empty response: {response_data(response)!r}")

    usage = _usage_dict(getattr(response, "usage", None))
    mode = "doubao_native" if web_search and searched else ("doubao_responses" if web_search else "none")
    if web_search and not searched:
        logger.info("Doubao responses completed without web_search_call (model skipped search)")

    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )


def doubao_chat_fallback(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout_s: float = 120.0,
) -> SamplingChatResult:
    """Fallback to chat/completions when Responses API web search fails."""
    text, usage, latency_ms = openai_chat_completion(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=messages,
        timeout_s=timeout_s,
        error_cls=DoubaoProviderError,
        provider_label="Doubao",
    )
    return SamplingChatResult(text=text, usage=usage, latency_ms=latency_ms)
