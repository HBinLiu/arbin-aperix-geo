"""DeepSeek web-crawl handler placeholder."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.geo_web_crawl.registry import register_platform


def handle_deepseek(payload: dict[str, Any], page: Any, context: Any) -> dict[str, Any]:
    _ = (payload, page, context)
    return {
        "ok": False,
        "error_type": "PlatformNotImplemented",
        "error": "platform deepseek web crawl is not implemented yet",
        "human_ops": False,
        "storage_state": None,
    }


register_platform("deepseek", handle_deepseek)
