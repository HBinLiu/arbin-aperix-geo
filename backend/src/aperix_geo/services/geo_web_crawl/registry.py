"""Platform handler registry for geo-web-crawl jobs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Handler = Callable[[dict[str, Any], Any, Any], dict[str, Any]]
# Handler(payload, page, context) -> result dict

_HANDLERS: dict[str, Handler] = {}


def register_platform(platform: str, handler: Handler) -> None:
    key = (platform or "").strip().lower()
    if not key:
        raise ValueError("platform name required")
    _HANDLERS[key] = handler


def get_handler(platform: str) -> Handler | None:
    return _HANDLERS.get((platform or "").strip().lower())


def list_platforms() -> list[str]:
    return sorted(_HANDLERS.keys())


def ensure_handlers_loaded() -> None:
    """Import handler modules so they register themselves."""
    from aperix_geo.services.geo_web_crawl.handlers import doubao as _doubao  # noqa: F401
    from aperix_geo.services.geo_web_crawl.handlers import deepseek as _deepseek  # noqa: F401
    from aperix_geo.services.geo_web_crawl.handlers import qianwen as _qianwen  # noqa: F401
