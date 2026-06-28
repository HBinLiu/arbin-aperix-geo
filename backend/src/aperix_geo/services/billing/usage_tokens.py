"""Normalize provider usage payloads into billing audit token counts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SETUP_LLM_PLATFORM = "deepseek"


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


def _coerce_nonneg_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def normalize_token_usage(usage: dict[str, Any] | None) -> TokenUsage:
    """Map OpenAI / Qianwen style usage dicts to input/output/total counts."""
    if not usage:
        return TokenUsage(0, 0, 0)

    input_tokens = _coerce_nonneg_int(usage.get("input_tokens") or usage.get("prompt_tokens"))
    output_tokens = _coerce_nonneg_int(usage.get("output_tokens") or usage.get("completion_tokens"))
    total_tokens = _coerce_nonneg_int(usage.get("total_tokens"))
    if total_tokens <= 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens
    return TokenUsage(input_tokens, output_tokens, total_tokens)
