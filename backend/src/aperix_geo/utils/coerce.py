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


def normalize_monitoring_scope(raw: dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    if region := raw.get("region"):
        if isinstance(region, str) and region.strip():
            out["region"] = region.strip()
    if language := raw.get("language"):
        if isinstance(language, str) and language.strip():
            out["language"] = language.strip()
    if note := raw.get("note"):
        if isinstance(note, str) and note.strip():
            out["note"] = note.strip()
    return out
