"""DeepSeek sampling · native web search via Anthropic-compatible Messages API."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.errors import DeepseekProviderError, raise_provider_error
from aperix_geo.services.providers._helpers import dedupe_urls
from aperix_geo.services.providers.openai import openai_chat_completion
from aperix_geo.services.providers.prompts import DEEPSEEK_WEB_SEARCH_SYSTEM
from aperix_geo.utils.net import extract_urls, filter_citation_urls

logger = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "2023-06-01"
_MAX_MESSAGE_ITERATIONS = 5
_DEFAULT_WEB_SEARCH_TOOL_TYPE = "web_search_20250305"
_KNOWN_WEB_SEARCH_TOOL_TYPES = frozenset(
    {
        "web_search_20250305",
        "web_search_20260209",
    }
)


def normalize_web_search_tool_type(tool_type: str) -> str:
    """Validate Anthropic web_search tool type (web_search_YYYYMMDD)."""
    value = (tool_type or _DEFAULT_WEB_SEARCH_TOOL_TYPE).strip()
    if value not in _KNOWN_WEB_SEARCH_TOOL_TYPES:
        known = ", ".join(sorted(_KNOWN_WEB_SEARCH_TOOL_TYPES))
        raise DeepseekProviderError(
            f"DeepSeek unsupported web_search tool type {value!r}; known: {known}"
        )
    return value


def build_web_search_tool(*, tool_type: str, max_uses: int) -> dict[str, Any]:
    return {
        "type": normalize_web_search_tool_type(tool_type),
        "name": "web_search",
        "max_uses": max(1, max_uses),
    }


def resolve_deepseek_anthropic_base_url(base_url: str, anthropic_base_url: str = "") -> str:
    explicit = anthropic_base_url.strip()
    if explicit:
        return explicit.rstrip("/")
    url = base_url.strip().rstrip("/")
    if url.endswith("/anthropic"):
        return url
    if url.endswith("/v1"):
        url = url[: -len("/v1")]
    return f"{url}/anthropic"


def _split_system_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    rest: list[dict[str, str]] = []
    for message in messages:
        if message.get("role") == "system":
            content = (message.get("content") or "").strip()
            if content:
                system_parts.append(content)
        else:
            rest.append(message)
    return "\n\n".join(system_parts), rest


def _to_anthropic_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if not content or role not in {"user", "assistant"}:
            continue
        out.append({"role": role, "content": [{"type": "text", "text": content}]})
    return out


def _collect_urls_from_block(block: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    block_type = block.get("type")
    if block_type == "web_search_tool_result":
        for item in block.get("content") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "web_search_result" and item.get("url"):
                urls.append(str(item["url"]))
    elif block_type == "text":
        for citation in block.get("citations") or []:
            if isinstance(citation, dict) and citation.get("url"):
                urls.append(str(citation["url"]))
    return urls


def parse_deepseek_anthropic_payload(data: dict[str, Any]) -> tuple[str, tuple[str, ...], bool]:
    texts: list[str] = []
    urls: list[str] = []
    searched = False

    for block in data.get("content") or []:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = str(block.get("text") or "").strip()
            if text:
                texts.append(text)
        elif block_type == "server_tool_use" and block.get("name") == "web_search":
            searched = True
        elif block_type == "web_search_tool_result":
            searched = True
        urls.extend(_collect_urls_from_block(block))

    usage = data.get("usage") or {}
    server_tool_use = usage.get("server_tool_use") or {}
    if int(server_tool_use.get("web_search_requests") or 0) > 0:
        searched = True

    text = "\n".join(texts).strip()
    urls.extend(filter_citation_urls(extract_urls(text)))
    source_urls = dedupe_urls(urls)
    return text, source_urls, searched


def _usage_from_anthropic(data: dict[str, Any]) -> dict[str, Any]:
    usage = data.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _merge_usage(total: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = dict(total)
    for key in ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens"):
        if key in current:
            merged[key] = int(merged.get(key, 0)) + int(current[key])
    return merged


def _raise_deepseek_http_error(response: httpx.Response, *, cause: BaseException | None = None) -> None:
    detail = response.text[:800]
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            detail = str(error.get("message") or error)[:800]
    except Exception:
        pass
    raise_provider_error(
        DeepseekProviderError,
        f"DeepSeek HTTP {response.status_code}: {detail}",
        status_code=response.status_code,
        cause=cause,
        provider_id="deepseek",
    )


def deepseek_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    anthropic_base_url: str = "",
    web_search: bool = True,
    web_search_tool_type: str = _DEFAULT_WEB_SEARCH_TOOL_TYPE,
    web_search_max_uses: int = 5,
    timeout_s: float = 120.0,
    temperature: float = 0.3,
) -> SamplingChatResult:
    if not web_search:
        text, usage, latency_ms = openai_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            timeout_s=timeout_s,
            error_cls=DeepseekProviderError,
            provider_label="DeepSeek",
        )
        return SamplingChatResult(
            text=text.strip(),
            usage=usage,
            latency_ms=latency_ms,
            web_search_mode="none",
        )

    if not api_key.strip():
        raise DeepseekProviderError("DeepSeek API key is not configured")
    if not model.strip():
        raise DeepseekProviderError("DeepSeek model is not configured")

    anthropic_base = resolve_deepseek_anthropic_base_url(base_url, anthropic_base_url)
    user_system, conversation = _split_system_messages(messages)
    system_parts = [part for part in (DEEPSEEK_WEB_SEARCH_SYSTEM, user_system) if part.strip()]
    system_text = "\n\n".join(system_parts)
    anthropic_messages = _to_anthropic_messages(conversation)
    if not anthropic_messages:
        raise DeepseekProviderError("DeepSeek web search requires at least one user message")

    tools = [build_web_search_tool(tool_type=web_search_tool_type, max_uses=web_search_max_uses)]
    endpoint = f"{anthropic_base}/v1/messages"
    headers = {
        "x-api-key": api_key.strip(),
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model.strip(),
        "max_tokens": 8192,
        "messages": anthropic_messages,
        "tools": tools,
        "temperature": temperature,
    }
    if system_text:
        body["system"] = system_text

    logger.info(
        "DeepSeek Anthropic Messages: model=%s messages=%d web_search=True tool=%s",
        model,
        len(anthropic_messages),
        normalize_web_search_tool_type(web_search_tool_type),
    )
    t0 = time.perf_counter()
    usage: dict[str, Any] = {}
    final_data: dict[str, Any] = {}
    iterations = 0

    with httpx.Client(timeout=timeout_s) as client:
        while iterations < _MAX_MESSAGE_ITERATIONS:
            iterations += 1
            try:
                response = client.post(endpoint, headers=headers, json=body)
            except httpx.TimeoutException as exc:
                raise_provider_error(
                    DeepseekProviderError,
                    f"DeepSeek timeout: {exc}",
                    retryable=False,
                    cause=exc,
                    provider_id="deepseek",
                )
            except httpx.HTTPError as exc:
                raise_provider_error(
                    DeepseekProviderError,
                    f"DeepSeek HTTP error: {exc}",
                    cause=exc,
                    provider_id="deepseek",
                )

            if response.status_code >= 400:
                _raise_deepseek_http_error(response)

            data = response.json()
            if not isinstance(data, dict):
                raise DeepseekProviderError(f"DeepSeek unexpected response shape: {data!r}")

            usage = _merge_usage(usage, _usage_from_anthropic(data))
            final_data = data
            stop_reason = data.get("stop_reason")

            if stop_reason == "pause_turn":
                anthropic_messages.append(
                    {
                        "role": "assistant",
                        "content": data.get("content") or [],
                    }
                )
                body["messages"] = anthropic_messages
                continue
            break

    if iterations >= _MAX_MESSAGE_ITERATIONS and final_data.get("stop_reason") == "pause_turn":
        raise DeepseekProviderError(
            f"DeepSeek web search exceeded {_MAX_MESSAGE_ITERATIONS} pause_turn iterations"
        )

    latency_ms = int((time.perf_counter() - t0) * 1000)
    text, source_urls, searched = parse_deepseek_anthropic_payload(final_data)
    if not text:
        raise DeepseekProviderError(f"DeepSeek empty response: {final_data!r}")

    if searched:
        mode = "deepseek_native"
    else:
        mode = "deepseek_chat"
        logger.info("DeepSeek chat completed without web_search blocks (model skipped search)")

    logger.info(
        "DeepSeek response: latency_ms=%d chars=%d source_urls=%d mode=%s",
        latency_ms,
        len(text),
        len(source_urls),
        mode,
    )
    from aperix_geo.services.alerts.dispatch import maybe_report_provider_success

    maybe_report_provider_success("deepseek")

    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )
