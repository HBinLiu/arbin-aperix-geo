"""Process-local Chromium reuse for Doubao Web (Playwright sync API).

Why: cold-starting Chromium each sample dominates latency. Keep one Browser warm
per worker process; each crawl still gets an isolated BrowserContext from
``storage_state`` so accounts never share cookies/DOM.

Constraints: Playwright sync API is not thread-safe — sessions in this process
are serialized by a lock. Prefer Celery prefork (one task per process) or keep
``DOUBAO_CRAWL_CONCURRENCY`` low when using threads.

Celery prefork: never call playwright.stop()/browser.close() on objects inherited
from the parent after fork — only drop references, then start fresh in the child.
Also reset the inherited asyncio event loop before ``sync_playwright().__enter__``;
otherwise the greenlet dispatcher returns without setting ``_playwright`` and raises
``AttributeError: ... has no attribute '_playwright'``.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from aperix_geo.config import Settings

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_PW_CM: Any | None = None
_PLAYWRIGHT: Any | None = None
_BROWSER: Any | None = None
_BROWSER_HEADLESS: bool | None = None


def discard_browser_pool_inherited() -> None:
    """Drop in-process Playwright refs without stopping drivers (post-fork safe)."""
    global _PW_CM, _PLAYWRIGHT, _BROWSER, _BROWSER_HEADLESS
    with _LOCK:
        _PW_CM = None
        _PLAYWRIGHT = None
        _BROWSER = None
        _BROWSER_HEADLESS = None


def prepare_sync_playwright_runtime() -> None:
    """Make Sync Playwright startable in a Celery prefork child.

    After fork the inherited asyncio loop / greenlet state is unsafe. Replacing
    the loop avoids PlaywrightContextManager.__enter__ returning without
    assigning ``_playwright``.
    """
    import asyncio

    discard_browser_pool_inherited()
    try:
        try:
            if asyncio.get_running_loop() is not None:
                logger.warning(
                    "doubao crawl: asyncio loop already running; sync Playwright may fail"
                )
                return
        except RuntimeError:
            pass
        asyncio.set_event_loop(asyncio.new_event_loop())
    except Exception:
        logger.debug("prepare_sync_playwright_runtime failed", exc_info=True)


def reset_browser_pool() -> None:
    """Close shared browser + playwright (tests / crash recovery in same process)."""
    global _PW_CM, _PLAYWRIGHT, _BROWSER, _BROWSER_HEADLESS
    with _LOCK:
        browser = _BROWSER
        playwright = _PLAYWRIGHT
        pw_cm = _PW_CM
        _BROWSER = None
        _PLAYWRIGHT = None
        _PW_CM = None
        _BROWSER_HEADLESS = None
    if browser is not None:
        try:
            browser.close()
        except Exception:
            logger.debug("browser close during reset failed", exc_info=True)
    if pw_cm is not None:
        try:
            # Only exit if enter progressed far enough to create a connection.
            if getattr(pw_cm, "_connection", None) is not None or getattr(
                pw_cm, "_playwright", None
            ) is not None:
                pw_cm.__exit__(None, None, None)
        except Exception:
            logger.debug("playwright context manager exit failed", exc_info=True)
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    logger.debug("playwright stop during reset failed", exc_info=True)
    elif playwright is not None:
        try:
            playwright.stop()
        except Exception:
            logger.debug("playwright stop during reset failed", exc_info=True)


def _browser_alive(browser: Any) -> bool:
    try:
        return bool(browser.is_connected())
    except Exception:
        return False


def _safe_cm_exit(cm: Any) -> None:
    try:
        if getattr(cm, "_connection", None) is not None or getattr(cm, "_playwright", None) is not None:
            cm.__exit__(None, None, None)
    except Exception:
        logger.debug("playwright cm exit skipped/failed", exc_info=True)


def _start_playwright() -> tuple[Any, Any]:
    """Start sync Playwright; return ``(context_manager, playwright)``."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    prepare_sync_playwright_runtime()
    cm = sync_playwright()
    try:
        playwright = cm.__enter__()
    except Exception:
        _safe_cm_exit(cm)
        raise
    if getattr(cm, "_playwright", None) is None:
        _safe_cm_exit(cm)
        raise RuntimeError("playwright sync enter returned without _playwright (fork/runtime)")
    return cm, playwright


def _ensure_shared_browser(*, headless: bool) -> Any:
    global _PW_CM, _PLAYWRIGHT, _BROWSER, _BROWSER_HEADLESS
    with _LOCK:
        if (
            _BROWSER is not None
            and _BROWSER_HEADLESS is headless
            and _browser_alive(_BROWSER)
        ):
            return _BROWSER

        # Headless flipped or dead process → rebuild.
        if _BROWSER is not None or _PLAYWRIGHT is not None or _PW_CM is not None:
            reset_browser_pool()

        cm, playwright = _start_playwright()
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Exception:
            _safe_cm_exit(cm)
            raise

        _PW_CM = cm
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


def _oneshot_browser_page_session(
    *,
    headless: bool,
    storage_state: dict[str, Any],
    timeout_ms: int,
) -> Iterator[tuple[Any, Any]]:
    """Launch a fresh Playwright driver for one crawl (Celery-safe fallback)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    prepare_sync_playwright_runtime()
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


def _want_browser_reuse(settings: Settings) -> bool:
    """Reuse is optional; under Celery prefer oneshot unless explicitly enabled."""
    configured = bool(getattr(settings, "doubao_crawl_browser_reuse", True))
    if not configured:
        return False
    # sampling_llm runs on the Celery llm worker — Sync Playwright + shared driver is fragile.
    if (os.environ.get("CELERY_WORKER_ROLE") or "").strip():
        return False
    return True


@contextmanager
def browser_page_session(
    settings: Settings,
    *,
    storage_state: dict[str, Any],
) -> Iterator[tuple[Any, Any]]:
    """Yield ``(page, context)`` for one crawl; always closes the context.

    When ``doubao_crawl_browser_reuse`` is true (and not under Celery), Chromium stays
    warm in-process. Otherwise (or on shared-driver failure) use a one-shot driver.
    """
    headless = bool(settings.doubao_crawl_headless)
    reuse = _want_browser_reuse(settings)
    timeout_ms = min(60_000, int(settings.doubao_crawl_timeout_s * 1000))

    if not reuse:
        yield from _oneshot_browser_page_session(
            headless=headless,
            storage_state=storage_state,
            timeout_ms=timeout_ms,
        )
        return

    shared_error: Exception | None = None
    with _LOCK:
        try:
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
                return
            except Exception:
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
        except Exception as exc:
            shared_error = exc
            discard_browser_pool_inherited()

    logger.warning(
        "shared browser unavailable (%s); falling back to one-shot Playwright",
        shared_error,
    )
    yield from _oneshot_browser_page_session(
        headless=headless,
        storage_state=storage_state,
        timeout_ms=timeout_ms,
    )


def _register_fork_hook() -> None:
    if not hasattr(os, "register_at_fork"):
        return
    try:
        os.register_at_fork(after_in_child=discard_browser_pool_inherited)
    except Exception:
        logger.debug("register_at_fork for doubao browser failed", exc_info=True)


_register_fork_hook()
atexit.register(reset_browser_pool)
