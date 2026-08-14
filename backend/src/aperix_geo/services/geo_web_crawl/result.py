"""Minimal geo-web-crawl failure envelope (CLI / jobs / runtime)."""

from __future__ import annotations

from typing import Any


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
        "storage_state": None,
    }
