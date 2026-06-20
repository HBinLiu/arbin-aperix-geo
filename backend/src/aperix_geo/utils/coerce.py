"""Safe type coercion and dict value helpers."""

from __future__ import annotations

from typing import Any


def pick_str(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def safe_int(data: dict[str, Any], key: str, default: int = 0) -> int:
    val = data.get(key, default)
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def safe_float(data: dict[str, Any], key: str) -> float | None:
    val = data.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
