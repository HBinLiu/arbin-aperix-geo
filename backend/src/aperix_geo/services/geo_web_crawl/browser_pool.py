"""Browser sessions for geo-web-crawl jobs.

Two backends:
- **Browserless** (preferred): ``GEO_WEB_CRAWL_BROWSER_WS_URL`` → per-job connect/close
- **Local Chromium**: warm Sync browser per worker thread (dev / no Browserless)
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

_local = threading.local()


def _headless_default() -> bool:
    raw = (os.environ.get("GEO_WEB_CRAWL_HEADLESS") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def browser_backend() -> str:
    """``browserless`` when WS URL is set, else ``local``."""
    return "browserless" if resolve_browser_ws_url() else "local"


def resolve_browser_ws_url() -> str:
    """WebSocket endpoint for Browserless / CDP remote browser.

    Examples:
      ws://browserless:3000/chromium/playwright?token=secret
      ws://127.0.0.1:3000?token=secret   # CDP (connect_over_cdp)
    """
    raw = (os.environ.get("GEO_WEB_CRAWL_BROWSER_WS_URL") or "").strip()
    if not raw:
        return ""
    token = (os.environ.get("GEO_WEB_CRAWL_BROWSERLESS_TOKEN") or "").strip()
    if not token:
        return raw
    parsed = urlparse(raw)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "token" not in q:
        q["token"] = token
        raw = urlunparse(parsed._replace(query=urlencode(q)))
    return raw


def _use_playwright_native(ws_url: str) -> bool:
    """True only for Browserless Playwright-protocol paths (strict version match)."""
    path = (urlparse(ws_url).path or "").lower()
    return "playwright" in path


def _teardown_thread_browser() -> None:
    browser = getattr(_local, "browser", None)
    pw_cm = getattr(_local, "pw_cm", None)
    _local.browser = None
    _local.playwright = None
    _local.pw_cm = None
    if browser is not None:
        try:
            browser.close()
        except Exception:
            logger.debug("browser close failed", exc_info=True)
    if pw_cm is not None:
        try:
            pw_cm.__exit__(None, None, None)
        except Exception:
            logger.debug("playwright cm exit failed", exc_info=True)


def _ensure_thread_browser(*, headless: bool | None = None) -> Any:
    """Start Sync Playwright + Chromium once per worker thread (local backend)."""
    want_headless = _headless_default() if headless is None else bool(headless)
    browser = getattr(_local, "browser", None)
    if browser is not None and getattr(_local, "headless", None) is want_headless:
        try:
            if browser.is_connected():
                return browser
        except Exception:
            pass
        _teardown_thread_browser()

    from playwright.sync_api import sync_playwright

    from aperix_geo.services.providers.doubao_web.browser import prepare_sync_playwright_runtime

    prepare_sync_playwright_runtime()
    pw_cm = sync_playwright()
    playwright = pw_cm.start()
    browser = playwright.chromium.launch(headless=want_headless)
    _local.pw_cm = pw_cm
    _local.playwright = playwright
    _local.browser = browser
    _local.headless = want_headless
    logger.info(
        "geo-web-crawl: local thread browser started headless=%s thread=%s",
        want_headless,
        threading.current_thread().name,
    )
    return browser


def shutdown_all_browsers() -> None:
    """Tear down local warm browser for the current thread."""
    _teardown_thread_browser()


def _cookie_names(cookies: object) -> set[str]:
    names: set[str] = set()
    if not isinstance(cookies, list):
        return names
    for cookie in cookies:
        if isinstance(cookie, dict):
            name = str(cookie.get("name") or "")
            if name:
                names.add(name)
    return names


def open_browser_context(
    browser: Any,
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
) -> Any:
    """Create or reuse a context and force-apply cookies.

    Browserless CDP (``connect_over_cdp``) already has a default context;
    ``new_context(storage_state=)`` often looks successful while Chrome never
    sends the session cookies. Reuse ``contexts[0]`` and always ``add_cookies``.
    """
        from aperix_geo.services.crawl_accounts.cookies import (
        playwright_cookies_for_context,
        playwright_cookies_with_url,
        playwright_storage_state_for_context,
    )

    cookies = playwright_cookies_for_context(storage_state)
    slim = playwright_storage_state_for_context(storage_state)
    borrowed = False
    try:
        existing_n = len(browser.contexts)
    except Exception:
        existing_n = 0
    if existing_n:
        context = browser.contexts[0]
        borrowed = True
        logger.info("geo-web-crawl cookie inject reuse existing CDP context")
        try:
            for page in list(context.pages):
                page.close()
        except Exception:
            logger.debug("borrowed context leftover page close failed", exc_info=True)
        try:
            context.clear_cookies()
        except Exception:
            logger.debug("borrowed context clear_cookies failed", exc_info=True)
    else:
        try:
            context = browser.new_context(
                storage_state=slim,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
        except Exception:
            logger.warning(
                "new_context(storage_state=) failed; retrying empty context + add_cookies",
                exc_info=True,
            )
            context = browser.new_context(
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
    try:
        context._aperix_borrowed = borrowed
    except Exception:
        pass
    context.set_default_timeout(max(1_000, int(timeout_ms)))
    try:
        context.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        logger.debug("clipboard permission grant skipped", exc_info=True)
    if cookies:
        applied: set[str] = set()
        try:
            context.add_cookies(cookies)
        except Exception:
            logger.warning("geo-web-crawl add_cookies(domain) failed; retry url", exc_info=True)
            try:
                context.add_cookies(playwright_cookies_with_url(cookies))
            except Exception:
                logger.warning(
                    "geo-web-crawl add_cookies(url) failed names=%s",
                    sorted(_cookie_names(cookies)),
                    exc_info=True,
                )
        try:
            applied = _cookie_names(context.cookies())
        except Exception:
            logger.debug("context.cookies() after add_cookies failed", exc_info=True)
        wanted = _cookie_names(cookies)
        missing = wanted - applied
        logger.info(
            "geo-web-crawl cookie inject borrowed=%s wanted=%s applied=%s missing=%s",
            borrowed,
            sorted(wanted),
            sorted(applied),
            sorted(missing),
        )
        if missing:
            try:
                context.add_cookies(playwright_cookies_with_url(cookies))
                applied = _cookie_names(context.cookies())
                logger.info(
                    "geo-web-crawl cookie inject url-retry applied=%s",
                    sorted(applied),
                )
            except Exception:
                logger.warning(
                    "geo-web-crawl cookie inject url-retry failed missing=%s",
                    sorted(missing),
                    exc_info=True,
                )
    return context


def _close_job_context(context: Any) -> None:
    borrowed = bool(getattr(context, "_aperix_borrowed", False))
    if borrowed:
        try:
            pages = list(context.pages)
        except Exception:
            pages = []
        for page in pages:
            try:
                page.close()
            except Exception:
                logger.debug("borrowed context page close failed", exc_info=True)
        return
    try:
        context.close()
    except Exception:
        logger.debug("context close failed", exc_info=True)


@contextmanager
def _page_session_browserless(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
    ws_url: str,
) -> Iterator[tuple[Any, Any]]:
    """Per-job connect to Browserless so concurrency slots are released promptly."""
    from playwright.sync_api import sync_playwright

    native = _use_playwright_native(ws_url)
    logger.info(
        "geo-web-crawl: browserless connect mode=%s thread=%s",
        "playwright" if native else "cdp",
        threading.current_thread().name,
    )
    pw_cm = sync_playwright()
    playwright = pw_cm.start()
    browser = None
    context = None
    try:
        if native:
            browser = playwright.chromium.connect(ws_url)
        else:
            browser = playwright.chromium.connect_over_cdp(ws_url)
        context = open_browser_context(browser, storage_state=storage_state, timeout_ms=timeout_ms)
        page = context.new_page()
        yield page, context
    finally:
        if context is not None:
            _close_job_context(context)
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.debug("browserless browser close failed", exc_info=True)
        try:
            pw_cm.__exit__(None, None, None)
        except Exception:
            logger.debug("browserless playwright exit failed", exc_info=True)


@contextmanager
def _page_session_local(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
    headless: bool | None = None,
) -> Iterator[tuple[Any, Any]]:
    browser = _ensure_thread_browser(headless=headless)
    context = open_browser_context(browser, storage_state=storage_state, timeout_ms=timeout_ms)
    page = context.new_page()
    try:
        yield page, context
    finally:
        _close_job_context(context)


@contextmanager
def page_session(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
    headless: bool | None = None,
) -> Iterator[tuple[Any, Any]]:
    """Yield ``(page, context)``; always closes the context (and Browserless browser)."""
    ws_url = resolve_browser_ws_url()
    if ws_url:
        with _page_session_browserless(
            storage_state=storage_state,
            timeout_ms=timeout_ms,
            ws_url=ws_url,
        ) as pair:
            yield pair
        return
    with _page_session_local(
        storage_state=storage_state,
        timeout_ms=timeout_ms,
        headless=headless,
    ) as pair:
        yield pair
