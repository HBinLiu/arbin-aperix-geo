"""Qianwen web-crawl handler placeholder."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.crawl_browser.registry import register_platform


def handle_qianwen(payload: dict[str, Any], page: Any, context: Any) -> dict[str, Any]:
    _ = (payload, page, context)
    return {
        "ok": False,
        "error_type": "PlatformNotImplemented",
        "error": "platform qianwen web crawl is not implemented yet",
        "human_ops": False,
        "storage_state": None,
    }


register_platform("qianwen", handle_qianwen)
