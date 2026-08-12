"""Process-local Chromium reuse for Doubao Web (Playwright sync API).

Why: cold-starting Chromium each sample dominates latency. Keep one Browser warm
per worker process; each crawl still gets an isolated BrowserContext from
``storage_state`` so accounts never share cookies/DOM.

Constraints: Playwright sync API is not thread-safe — sessions in this process
are serialized by a lock. Prefer Celery prefork (one task per process) or keep
``DOUBAO_CRAWL_CONCURRENCY`` low when using threads.
"""

from __future__ import annotations

import atexit
import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from aperix_geo.config import Settings

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_PLAYWRIGHT: Any | None = None
_BROWSER: Any | None = None
_BROWSER_HEADLESS: bool | None = None


def reset_browser_pool() -> None:
    """Close shared browser + playwright (tests / crash recovery)."""
    global _PLAYWRIGHT, _BROWSER, _BROWSER_HEADLESS
    with _LOCK:
        browser = _BROWSER
        playwright = _PLAYWRIGHT
        _BROWSER = None
        _PLAYWRIGHT = None
        _BROWSER_HEADLESS = None
    if browser is not None:
        try:
            browser.close()
        except Exception:
            logger.debug("browser close during reset failed", exc_info=True)
    if playwright is not None:
        try:
            playwright.stop()
        except Exception:
            logger.debug("playwright stop during reset failed", exc_info=True)


def _browser_alive(browser: Any) -> bool:
    try:
        return bool(browser.is_connected())
    except Exception:
        return False


def _ensure_shared_browser(*, headless: bool) -> Any:
    global _PLAYWRIGHT, _BROWSER, _BROWSER_HEADLESS
    with _LOCK:
        if (
            _BROWSER is not None
            and _BROWSER_HEADLESS is headless
            and _browser_alive(_BROWSER)
        ):
            return _BROWSER

        # Headless flipped or dead process → rebuild.
        if _BROWSER is not None or _PLAYWRIGHT is not None:
            reset_browser_pool()

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("playwright is not installed") from exc

        # sync_playwright().__enter__ starts the driver; we keep it for process life.
        playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Exception:
            try:
                playwright.stop()
            except Exception:
                pass
            raise

        _PLAYWRIGHT = playwright
        _BROWSER = browser
        _BROWSER_HEADLESS = headless
        logger.info("doubao crawl browser started (reuse) headless=%s", headless)
        return browser


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
    """Yield ``(page, context)`` for one crawl; always closes the context.

    When ``doubao_crawl_browser_reuse`` is true, Chromium stays warm in-process.
    When false, launch + full teardown per call (debug / headed one-shots).
    """
    headless = bool(settings.doubao_crawl_headless)
    reuse = bool(getattr(settings, "doubao_crawl_browser_reuse", True))
    timeout_ms = min(60_000, int(settings.doubao_crawl_timeout_s * 1000))

    if not reuse:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("playwright is not installed") from exc
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
        return

    # Serialize sync Playwright usage in this process.
    with _LOCK:
        browser = _ensure_shared_browser(headless=headless)
        context = None
        try:
            try:
                context = _open_context(
                    browser,
                    storage_state=storage_state,
                    default_timeout_ms=timeout_ms,
                )
            except Exception:
                logger.warning("new_context failed; resetting browser pool", exc_info=True)
                reset_browser_pool()
                browser = _ensure_shared_browser(headless=headless)
                context = _open_context(
                    browser,
                    storage_state=storage_state,
                    default_timeout_ms=timeout_ms,
                )
            page = context.new_page()
            yield page, context
        except Exception:
            # Browser may be wedged after driver errors — recycle for next call.
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
                context = None
            if browser is not None and not _browser_alive(browser):
                reset_browser_pool()
            raise
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    logger.debug("context close failed", exc_info=True)
                    reset_browser_pool()


atexit.register(reset_browser_pool)
