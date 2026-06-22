"""Sanitize values before PostgreSQL text/JSONB storage."""

from __future__ import annotations

from typing import Any


def sanitize_text(value: str) -> str:
    """Remove NULL bytes and other characters PostgreSQL text/JSONB reject."""
    if not value:
        return value or ""
    cleaned = value.replace("\x00", "")
    # Surrogate pairs can break some JSON encoders; round-trip via UTF-8.
    return cleaned.encode("utf-8", errors="replace").decode("utf-8")


def sanitize_json_value(value: Any) -> Any:
    """Recursively sanitize strings inside JSON-serializable structures."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return {
            sanitize_text(str(key)): sanitize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_json_value(item) for item in value]
    return sanitize_text(str(value))
