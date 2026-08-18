"""Sync Playwright helpers for local scripts only (login helper / smoke).

Production sampling and heartbeat use geo-web-crawl (HTTP service).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from aperix_geo.config import Settings
from aperix_geo.services.crawl_browser.browser_pool import prepare_sync_playwright_runtime

logger = logging.getLogger(__name__)

__all__ = [
    "browser_page_session",
    "prepare_sync_playwright_runtime",
]


@contextmanager
def browser_page_session(
    settings: Settings,
    *,
    storage_state: dict[str, Any],
) -> Iterator[tuple[Any, Any]]:
    """Yield ``(page, context)`` for one local script run; closes browser afterward."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    prepare_sync_playwright_runtime()
    headless = bool(settings.doubao_crawl_headless)
    timeout_ms = min(60_000, int(settings.doubao_crawl_timeout_s * 1000))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = None
        try:
            context = browser.new_context(
                storage_state=storage_state,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
            context.set_default_timeout(max(1_000, int(timeout_ms)))
            try:
                context.grant_permissions(["clipboard-read", "clipboard-write"])
            except Exception:
                logger.debug("clipboard permission grant skipped", exc_info=True)
            yield context.new_page(), context
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    logger.debug("context close failed", exc_info=True)
            try:
                browser.close()
            except Exception:
                logger.debug("browser close failed", exc_info=True)
