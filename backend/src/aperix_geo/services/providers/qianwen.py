"""Alibaba DashScope · Qwen Generation API via official dashscope SDK (web search)."""

from __future__ import annotations

import logging
import time
from http import HTTPStatus
from typing import Any

import dashscope
from dashscope import Generation

from aperix_geo.services.chat_result import SamplingChatResult
from aperix_geo.services.providers._helpers import dedupe_urls, to_plain, with_system_prompt
from aperix_geo.services.providers.errors import QianwenProviderError
from aperix_geo.services.providers.prompts import QIANWEN_WEB_SEARCH_SYSTEM

logger = logging.getLogger(__name__)


def dashscope_http_api_url(base_url: str) -> str:
    """Normalize DashScope SDK base URL (expects .../api/v1)."""
    base = base_url.strip().rstrip("/")
    if not base:
        return "https://dashscope.aliyuncs.com/api/v1"
    if base.endswith("/api/v1"):
        return base
    if "/compatible-mode" in base:
        root = base.split("/compatible-mode", 1)[0].rstrip("/")
        return f"{root}/api/v1"
    return f"{base}/api/v1"


def _collect_search_urls(search_info: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in search_info.get("search_results") or []:
        if isinstance(item, dict) and item.get("url"):
            urls.append(str(item["url"]))
    for item in search_info.get("extra_tool_info") or []:
        if not isinstance(item, dict):
            continue
        for key in ("url", "link"):
            if item.get(key):
                urls.append(str(item[key]))
    return urls


def _search_used(data: dict[str, Any], search_info: dict[str, Any]) -> bool:
    if _collect_search_urls(search_info):
        return True
    usage = data.get("usage")
    if isinstance(usage, dict):
        plugins = usage.get("plugins")
        if isinstance(plugins, dict):
            search = plugins.get("search")
            if isinstance(search, dict) and int(search.get("count") or 0) > 0:
                return True
    return False


def parse_generation_payload(data: dict[str, Any] | Any) -> tuple[str, tuple[str, ...], bool]:
    if hasattr(data, "output"):
        payload = {
            "output": to_plain(getattr(data, "output", None) or {}),
            "usage": to_plain(getattr(data, "usage", None) or {}),
        }
    elif isinstance(data, dict):
        payload = data
    else:
        payload = to_plain(data)

    output = payload.get("output")
    if not isinstance(output, dict):
        output = {}

    text = ""
    choices = output.get("choices") or []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict):
            text = str(message.get("content") or "").strip()

    search_info = output.get("search_info")
    if not isinstance(search_info, dict):
        search_info = {}

    source_urls = dedupe_urls(_collect_search_urls(search_info))
    searched = _search_used(payload, search_info)
    return text, source_urls, searched


def qianwen_generation_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    web_search: bool = True,
    timeout_s: float = 120.0,
) -> SamplingChatResult:
    """Call DashScope Generation.call with optional enable_search."""
    if not api_key.strip():
        raise QianwenProviderError("Qianwen API key is not configured")
    if not model.strip():
        raise QianwenProviderError("Qianwen model is not configured")

    dashscope.base_http_api_url = dashscope_http_api_url(base_url)

    call_kwargs: dict[str, Any] = {
        "api_key": api_key.strip(),
        "model": model.strip(),
        "messages": with_system_prompt(messages, QIANWEN_WEB_SEARCH_SYSTEM),
        "result_format": "message",
        "request_timeout": timeout_s,
    }
    if web_search:
        call_kwargs["enable_search"] = True
        call_kwargs["search_options"] = {
            "enable_source": True,
            "enable_citation": True,
            "citation_format": "[ref_<number>]",
        }

    t0 = time.perf_counter()
    try:
        response = Generation.call(**call_kwargs)
    except Exception as exc:
        raise QianwenProviderError(f"Qianwen SDK error: {exc}") from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)

    status_code = getattr(response, "status_code", None)
    if status_code is not None and status_code != HTTPStatus.OK:
        message = str(getattr(response, "message", "") or "")[:800]
        code = getattr(response, "code", "") or status_code
        raise QianwenProviderError(f"Qianwen HTTP {status_code}: {code} {message}")

    code = getattr(response, "code", None)
    if code:
        message = str(getattr(response, "message", "") or "")[:800]
        raise QianwenProviderError(f"Qianwen API error {code}: {message}")

    text, source_urls, searched = parse_generation_payload(response)
    if not text:
        raise QianwenProviderError(f"Qianwen empty response: {response!r}")

    usage = to_plain(getattr(response, "usage", None) or {})
    if not isinstance(usage, dict):
        usage = {}

    if web_search and searched:
        mode = "qianwen_native"
    elif web_search:
        mode = "qianwen_generation"
        logger.info("Qianwen generation completed without search_results (model skipped search)")
    else:
        mode = "none"

    return SamplingChatResult(
        text=text,
        usage=usage,
        latency_ms=latency_ms,
        source_urls=source_urls,
        web_search_mode=mode,
    )
