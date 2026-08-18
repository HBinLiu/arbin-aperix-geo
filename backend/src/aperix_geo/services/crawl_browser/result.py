"""Minimal crawl-browser failure envelope (CLI / jobs / HTTP client)."""

from __future__ import annotations

from typing import Any


def context_timeout_ms(timeout_s: float) -> int:
    """Playwright context default timeout; allow full job budget (cap 15m)."""
    return max(10_000, min(900_000, int(float(timeout_s) * 1000)))


def crawl_fail(
    message: str,
    *,
    error_type: str = "CrawlError",
) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": error_type,
        "error": message,
        "human_ops": False,
        "session_alive": False,
        "storage_state": None,
    }
