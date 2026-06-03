"""OpenAI-compatible chat completion client."""

from __future__ import annotations

import time
from typing import Any

import httpx

from aperix_geo.config import get_settings


class LLMProviderError(Exception):
    pass


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    timeout_s: float = 120.0,
    json_mode: bool = False,
) -> tuple[str, dict[str, Any], int]:
    """Return (assistant_text, usage_dict, latency_ms)."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise LLMProviderError("DEEPSEEK_API_KEY is not configured")

    url = settings.deepseek_base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    t0 = time.perf_counter()
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, headers=headers, json=body)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    if resp.status_code >= 400:
        raise LLMProviderError(f"LLM HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise LLMProviderError(f"Unexpected LLM response shape: {data!r}") from e
    usage = data.get("usage") or {}
    return text, usage, latency_ms
