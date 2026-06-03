"""Generic OpenAI-compatible chat/completions HTTP client."""

from __future__ import annotations

import time
from typing import Any, Type

import httpx


def openai_chat_completion(
    *,
    url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    timeout_s: float = 120.0,
    json_mode: bool = False,
    error_cls: Type[Exception] = Exception,
    provider_label: str = "LLM",
) -> tuple[str, dict[str, Any], int]:
    """POST chat/completions; return (text, usage, latency_ms)."""
    if not api_key.strip():
        raise error_cls(f"{provider_label} API key is not configured")
    if not model.strip():
        raise error_cls(f"{provider_label} model is not configured")

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model.strip(),
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
        raise error_cls(f"{provider_label} HTTP {resp.status_code}: {resp.text[:800]}")
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise error_cls(f"Unexpected {provider_label} response shape: {data!r}") from e
    usage = data.get("usage") or {}
    return text, usage, latency_ms
