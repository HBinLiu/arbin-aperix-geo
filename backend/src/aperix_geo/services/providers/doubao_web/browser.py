"""Sync Playwright helpers for local scripts only (login helper / smoke).

Production sampling and heartbeat use ``geo-web-crawl`` (HTTP service or ``geo_web_crawl.cli``).
"""

from __future__ import annotations

import atexit
import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from aperix_geo.config import Settings

logger = logging.getLogger(__name__)


def discard_browser_pool_inherited() -> None:
    """No-op retained for Celery fork hooks / older call sites."""
    return


def prepare_sync_playwright_runtime() -> None:
    """Clear stale asyncio loop so Sync Playwright can start (local scripts)."""
    import asyncio

    discard_browser_pool_inherited()
    try:
        try:
            asyncio.get_running_loop()
            logger.warning(
                "doubao sync Playwright: asyncio loop already running; may fail"
            )
            return
        except RuntimeError:
            pass
        asyncio.set_event_loop(None)
    except Exception:
        logger.debug("prepare_sync_playwright_runtime failed", exc_info=True)


def reset_browser_pool() -> None:
    """Compatibility no-op."""
    return


def _open_context(
    browser: Any,
    *,
    storage_state: dict[str, Any],
    default_timeout_ms: int,
) -> Any:
    context = browser.new_context(
        storage_state=storage_state,
        locale="zh-CN",
        viewport={"width": 1440, "height": 900},
    )
    context.set_default_timeout(max(1_000, int(default_timeout_ms)))
    try:
        context.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        logger.debug("clipboard permission grant skipped", exc_info=True)
    return context


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
            context = _open_context(
                browser,
                storage_state=storage_state,
                default_timeout_ms=timeout_ms,
            )
            page = context.new_page()
            yield page, context
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


def _register_fork_hook() -> None:
    if not hasattr(os, "register_at_fork"):
        return
    try:
        os.register_at_fork(after_in_child=discard_browser_pool_inherited)
    except Exception:
        logger.debug("register_at_fork for doubao browser failed", exc_info=True)


_register_fork_hook()
atexit.register(reset_browser_pool)
