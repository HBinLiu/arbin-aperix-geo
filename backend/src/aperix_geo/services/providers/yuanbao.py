"""腾讯元宝 / 混元 Chat Completions 客户端（OpenAI 兼容）。"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from aperix_geo.config import get_settings

logger = logging.getLogger(__name__)

CHAT_TIMEOUT_S = 120.0


class YuanbaoProviderError(Exception):
    pass


def yuanbao_chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    timeout_s: float = CHAT_TIMEOUT_S,
    json_mode: bool = False,
) -> tuple[str, dict[str, Any], int]:
    """POST /chat/completions，返回 (text, usage, latency_ms)。"""
    settings = get_settings()
    api_key = settings.yuanbao_api_key.strip()
    model = settings.yuanbao_model.strip()
    if not api_key:
        raise YuanbaoProviderError("YUANBAO_API_KEY is not configured")
    if not model:
        raise YuanbaoProviderError("YUANBAO_MODEL is not configured")

    url = settings.yuanbao_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    logger.info("腾讯元宝 ChatCompletions: model=%s messages=%d", model, len(messages))
    t0 = time.perf_counter()
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, headers=headers, json=body)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    if resp.status_code >= 400:
        raise YuanbaoProviderError(f"Yuanbao HTTP {resp.status_code}: {resp.text[:800]}")
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise YuanbaoProviderError(f"Unexpected Yuanbao response shape: {data!r}") from e
    usage = data.get("usage") or {}
    logger.info("腾讯元宝响应: latency_ms=%d chars=%d", latency_ms, len(text))
    return text, usage, latency_ms
