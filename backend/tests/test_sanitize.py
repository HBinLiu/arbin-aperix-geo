"""Tests for PostgreSQL-safe sanitization."""

from __future__ import annotations

from aperix_geo.utils.sanitize import sanitize_json_value, sanitize_text


def test_sanitize_text_strips_null_bytes() -> None:
    raw = "before\x00after\ufffd\u0000tail"
    cleaned = sanitize_text(raw)
    assert "\x00" not in cleaned
    assert "\u0000" not in cleaned
    assert cleaned.startswith("before")
    assert cleaned.endswith("tail")


def test_sanitize_json_value_recurses() -> None:
    payload = {
        "snippet": "a\x00b",
        "nested": [{"title": "x\u0000y"}],
        "count": 3,
    }
    cleaned = sanitize_json_value(payload)
    assert cleaned["snippet"] == "ab"
    assert cleaned["nested"][0]["title"] == "xy"
    assert cleaned["count"] == 3
