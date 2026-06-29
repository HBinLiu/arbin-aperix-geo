"""Kimi / Moonshot sampling · OpenAI-compatible chat with native $web_search."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import APIError, APITimeoutError, OpenAI

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.errors import KimiProviderError
from aperix_geo.services.providers._helpers import (
    dedupe_urls,
    with_system_prompt,
)
from aperix_geo.services.providers.openai import (
    _raise_completion_error,
    _usage_dict,
    openai_chat_completion,
)
from aperix_geo.services.providers.prompts import KIMI_WEB_SEARCH_SYSTEM
from aperix_geo.utils.net import extract_urls, filter_citation_urls

logger = logging.getLogger(__name__)

_OPENAI_SAMPLING_MAX_RETRIES = 0
_KIMI_WEB_SEARCH_TOOL = {
    "type": "builtin_function",
    "function": {"name": "$web_search"},
}
_URL_KEYS = frozenset({"url", "Url", "link", "source_url", "SourceUrl"})


def _collect_urls_from_value(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _URL_KEYS and isinstance(item, str) and item.strip():
                urls.append(item.strip())
            else:
                urls.extend(_collect_urls_from_value(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_collect_urls_from_value(item))
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        urls.append(value.strip())
    return urls


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    dump = getattr(message, "model_dump", None)
    data = dump(exclude_none=True) if callable(dump) else {}
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning is not None and "reasoning_content" not in data:
        data["reasoning_content"] = reasoning
    return data


def parse_kimi_payload(
    text: str,
    *,
    searched: bool,
    tool_source_urls: list[str] | None = None,
) -> tuple[str, tuple[str, ...], bool]:
    urls = list(tool_source_urls or [])
    urls.extend(filter_citation_urls(extract_urls(text)))
    source_urls = dedupe_urls(urls)
    return text.strip(), source_urls, searched


def kimi_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    web_search: bool = True,
    web_search_max_uses: int = 5,
    timeout_s: float = 180.0,
    temperature: float = 1.0,
) -> SamplingChatResult:
    if not web_search:
        text, usage, latency_ms = openai_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            timeout_s=timeout_s,
            error_cls=KimiProviderError,
            provider_label="Kimi",
        )
        return SamplingChatResult(
            text=text.strip(),
            usage=usage,
            latency_ms=latency_ms,
            web_search_mode="none",
        )

    if not api_key.strip():
        raise KimiProviderError("Kimi API key is not configured")
    if not model.strip():
        raise KimiProviderError("Kimi model is not configured")
    if not base_url.strip():
        raise KimiProviderError("Kimi base_url is not configured")

    client = OpenAI(
        api_key=api_key.strip(),
        base_url=base_url.strip(),
        timeout=timeout_s,
        max_retries=_OPENAI_SAMPLING_MAX_RETRIES,
    )
    chat_messages: list[dict[str, Any]] = with_system_prompt(messages, KIMI_WEB_SEARCH_SYSTEM)

    logger.info(
        "Kimi ChatCompletions: model=%s messages=%d web_search=True",
        model,
        len(messages),
    )
    t0 = time.perf_counter()
    usage: dict[str, Any] = {}
    searched = False
    tool_source_urls: list[str] = []
    finish_reason: str | None = None
    text = ""
    iterations = 0
    max_iterations = max(1, web_search_max_uses)

    while finish_reason is None or finish_reason == "tool_calls":
        if iterations >= max_iterations:
            raise KimiProviderError(
                f"Kimi $web_search exceeded {max_iterations} tool-call iterations"
            )
        iterations += 1

        try:
            response = client.chat.completions.create(
                model=model.strip(),
                messages=chat_messages,
                temperature=temperature,
                stream=False,
                tools=[_KIMI_WEB_SEARCH_TOOL],
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError as exc:
            _raise_completion_error(
                KimiProviderError,
                f"Kimi timeout: {exc}",
                retryable=False,
                cause=exc,
                provider_label="Kimi",
            )
        except APIError as exc:
            detail = (getattr(exc, "message", None) or str(exc))[:800]
            status = getattr(exc, "status_code", None)
            if status is not None:
                _raise_completion_error(
                    KimiProviderError,
                    f"Kimi HTTP {status}: {detail}",
                    status_code=status,
                    cause=exc,
                    provider_label="Kimi",
                )
            _raise_completion_error(
                KimiProviderError,
                f"Kimi API error: {detail}",
                cause=exc,
                provider_label="Kimi",
            )
        except Exception as exc:
            _raise_completion_error(
                KimiProviderError,
                f"Kimi error: {exc}",
                cause=exc,
                provider_label="Kimi",
            )

        current_usage = _usage_dict(getattr(response, "usage", None))
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if key in current_usage:
                usage[key] = usage.get(key, 0) + int(current_usage[key])

        choice = response.choices[0]
        finish_reason = choice.finish_reason

        if finish_reason == "tool_calls":
            searched = True
            chat_messages.append(_assistant_message_dict(choice.message))
            for tool_call in choice.message.tool_calls or []:
                name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {"raw": raw_args}
                if name == "$web_search":
                    tool_source_urls.extend(_collect_urls_from_value(args))
                    tool_result: Any = args
                else:
                    tool_result = {"error": f"unknown tool {name}"}
                chat_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )
        else:
            text = str(choice.message.content or "").strip()

    latency_ms = int((time.perf_counter() - t0) * 1000)
    text, source_urls, searched = parse_kimi_payload(
        text,
        searched=searched,
        tool_source_urls=tool_source_urls,
    )
    if not text:
        raise KimiProviderError("Kimi empty response after $web_search")

    if searched:
        mode = "kimi_native"
    else:
        mode = "kimi_chat"
        logger.info("Kimi chat completed without $web_search tool_calls (model skipped search)")

    logger.info(
        "Kimi response: latency_ms=%d chars=%d source_urls=%d mode=%s",
        latency_ms,
        len(text),
        len(source_urls),
        mode,
    )
    from aperix_geo.services.alerts.billing import provider_id_from_message
    from aperix_geo.services.alerts.dispatch import maybe_report_provider_success

    provider_id = provider_id_from_message("Kimi HTTP")
    if provider_id != "unknown":
        maybe_report_provider_success(provider_id)

    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )
