"""Generic OpenAI-compatible chat/completions client (official SDK)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Type

from openai import APIError, APITimeoutError, OpenAI

from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.providers._helpers import (
    collect_url_field,
    dedupe_urls,
    extract_completion_text,
    response_data,
    with_system_prompt,
)
from aperix_geo.services.providers.errors import ProviderError, raise_provider_error

logger = logging.getLogger(__name__)


def _raise_completion_error(
    error_cls: Type[Exception],
    message: str,
    *,
    status_code: int | None = None,
    retryable: bool | None = None,
    cause: BaseException | None = None,
) -> None:
    if isinstance(error_cls, type) and issubclass(error_cls, ProviderError):
        raise_provider_error(
            error_cls,
            message,
            status_code=status_code,
            retryable=retryable,
            cause=cause,
        )
    raise error_cls(message) from cause


def _usage_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    dump = getattr(usage, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=True)
    return dict(usage)


def openai_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    timeout_s: float = 120.0,
    json_mode: bool = False,
    extra_body: dict[str, Any] | None = None,
    error_cls: Type[Exception] = Exception,
    provider_label: str = "LLM",
) -> tuple[str, dict[str, Any], int]:
    """Call chat/completions via OpenAI SDK; return (text, usage, latency_ms)."""
    if not api_key.strip():
        raise error_cls(f"{provider_label} API key is not configured")
    if not model.strip():
        raise error_cls(f"{provider_label} model is not configured")
    if not base_url.strip():
        raise error_cls(f"{provider_label} base_url is not configured")

    client = OpenAI(
        api_key=api_key.strip(),
        base_url=base_url.strip(),
        timeout=timeout_s,
    )
    kwargs: dict[str, Any] = {
        "model": model.strip(),
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if extra_body:
        kwargs["extra_body"] = extra_body

    t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(**kwargs)
    except APITimeoutError as e:
        _raise_completion_error(
            error_cls,
            f"{provider_label} timeout: {e}",
            retryable=True,
            cause=e,
        )
    except APIError as e:
        detail = (getattr(e, "message", None) or str(e))[:800]
        status = getattr(e, "status_code", None)
        if status is not None:
            _raise_completion_error(
                error_cls,
                f"{provider_label} HTTP {status}: {detail}",
                status_code=status,
                cause=e,
            )
        _raise_completion_error(error_cls, f"{provider_label} API error: {detail}", cause=e)
    except Exception as e:
        _raise_completion_error(error_cls, f"{provider_label} error: {e}", cause=e)

    latency_ms = int((time.perf_counter() - t0) * 1000)

    try:
        text = response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError) as e:
        raise error_cls(f"Unexpected {provider_label} response shape: {response!r}") from e

    return text, _usage_dict(response.usage), latency_ms


def parse_yuanbao_payload(response: Any) -> tuple[str, tuple[str, ...], bool]:
    data = response_data(response)
    text = extract_completion_text(response, data)

    search_info = data.get("search_info") or data.get("SearchInfo")
    if not isinstance(search_info, dict):
        search_info = {}

    results = search_info.get("search_results") or search_info.get("SearchResults") or []
    source_urls = dedupe_urls(collect_url_field(results if isinstance(results, list) else []))
    searched = bool(source_urls)
    if not searched:
        processes = data.get("processes") or data.get("Processes")
        if isinstance(processes, dict) and processes:
            searched = True
    return text, source_urls, searched


def parse_ernie_payload(response: Any) -> tuple[str, tuple[str, ...], bool]:
    data = response_data(response, extra_attrs=("search_results",))
    text = extract_completion_text(response, data)

    search_results = data.get("search_results") or []
    if not isinstance(search_results, list):
        search_results = []
    source_urls = dedupe_urls(collect_url_field(search_results))
    return text, source_urls, bool(source_urls)


@dataclass(frozen=True)
class OpenAIWebSearchSpec:
    provider_label: str
    error_cls: type[ProviderError]
    system_prompt: str
    native_mode: str
    fallback_mode: str
    build_extra_body: Callable[[], dict[str, Any]]
    parse_payload: Callable[[Any], tuple[str, tuple[str, ...], bool]]


def openai_web_search_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    spec: OpenAIWebSearchSpec,
    web_search: bool = True,
    timeout_s: float = 120.0,
    temperature: float = 0.3,
) -> SamplingChatResult:
    """Call chat/completions with web search via extra_body; return SamplingChatResult."""
    if not api_key.strip():
        raise spec.error_cls(f"{spec.provider_label} API key is not configured")
    if not model.strip():
        raise spec.error_cls(f"{spec.provider_label} model is not configured")
    if not base_url.strip():
        raise spec.error_cls(f"{spec.provider_label} base_url is not configured")

    client = OpenAI(
        api_key=api_key.strip(),
        base_url=base_url.strip(),
        timeout=timeout_s,
    )
    kwargs: dict[str, Any] = {
        "model": model.strip(),
        "messages": with_system_prompt(messages, spec.system_prompt),
        "temperature": temperature,
        "stream": False,
    }
    if web_search:
        kwargs["extra_body"] = spec.build_extra_body()

    logger.info(
        "%s ChatCompletions: model=%s messages=%d web_search=%s",
        spec.provider_label,
        model,
        len(messages),
        web_search,
    )
    t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(**kwargs)
    except APITimeoutError as exc:
        _raise_completion_error(
            spec.error_cls,
            f"{spec.provider_label} timeout: {exc}",
            retryable=True,
            cause=exc,
        )
    except APIError as exc:
        detail = (getattr(exc, "message", None) or str(exc))[:800]
        status = getattr(exc, "status_code", None)
        if status is not None:
            _raise_completion_error(
                spec.error_cls,
                f"{spec.provider_label} HTTP {status}: {detail}",
                status_code=status,
                cause=exc,
            )
        _raise_completion_error(
            spec.error_cls,
            f"{spec.provider_label} API error: {detail}",
            cause=exc,
        )
    except Exception as exc:
        _raise_completion_error(
            spec.error_cls,
            f"{spec.provider_label} error: {exc}",
            cause=exc,
        )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    text, source_urls, searched = spec.parse_payload(response)
    if not text:
        raise spec.error_cls(
            f"{spec.provider_label} empty response: {response_data(response)!r}"
        )

    usage = _usage_dict(getattr(response, "usage", None))
    if web_search and searched:
        mode = spec.native_mode
    elif web_search:
        mode = spec.fallback_mode
        logger.info(
            "%s chat completed without search_results (model skipped search)",
            spec.provider_label,
        )
    else:
        mode = "none"

    logger.info(
        "%s response: latency_ms=%d chars=%d source_urls=%d mode=%s",
        spec.provider_label,
        latency_ms,
        len(text),
        len(source_urls),
        mode,
    )
    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )
