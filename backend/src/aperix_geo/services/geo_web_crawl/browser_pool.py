"""Browser sessions for geo-web-crawl jobs.

Production: one Chromium ``user-data-dir`` per account (same dir as noVNC login).
Local smoke without ``account_id``: ephemeral ``chromium.launch`` + ``storage_state``.

Headless is ``GEO_WEB_CRAWL_HEADLESS`` only (not a per-job payload field).
"""

from __future__ import annotations

import fcntl
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1440, "height": 900}
_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


def _headless() -> bool:
    raw = (os.environ.get("GEO_WEB_CRAWL_HEADLESS") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def browser_backend() -> str:
    return "profile" if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() else "local"


def prepare_sync_playwright_runtime() -> None:
    """Clear a leftover asyncio loop so Sync Playwright can start."""
    import asyncio

    try:
        try:
            asyncio.get_running_loop()
            logger.warning("geo-web-crawl: asyncio loop already running; Sync Playwright may fail")
            return
        except RuntimeError:
            pass
        asyncio.set_event_loop(None)
    except Exception:
        logger.debug("prepare_sync_playwright_runtime failed", exc_info=True)


def parse_job_session(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    """Return ``(account_id, storage_state, platform)``.

    Production (``GEO_CRAWL_PROFILE_ROOT`` set) requires ``account_id``.
    Local smoke without a profile root requires ``storage_state``.
    """
    platform = str(payload.get("platform") or "doubao").strip().lower() or "doubao"
    account_id = str(payload.get("account_id") or "").strip()
    storage_state = payload.get("storage_state")
    if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() and not account_id:
        raise ValueError("account_id required when GEO_CRAWL_PROFILE_ROOT is set")
    if not account_id and not isinstance(storage_state, dict):
        raise ValueError("storage_state missing")
    if not isinstance(storage_state, dict):
        storage_state = {"cookies": []}
    return account_id, storage_state, platform


def _apply_context_defaults(context: Any, *, timeout_ms: int) -> None:
    context.set_default_timeout(max(1_000, int(timeout_ms)))
    try:
        context.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        logger.debug("clipboard permission grant skipped", exc_info=True)


@contextmanager
def _profile_lock(profile_dir: Path) -> Iterator[None]:
    profile_dir.mkdir(parents=True, exist_ok=True)
    fh = (profile_dir / ".aperix.lock").open("a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def _start_playwright():
    from playwright.sync_api import sync_playwright

    prepare_sync_playwright_runtime()
    pw_cm = sync_playwright()
    return pw_cm, pw_cm.start()


def _stop_playwright(pw_cm: Any) -> None:
    try:
        pw_cm.__exit__(None, None, None)
    except Exception:
        logger.debug("playwright exit failed", exc_info=True)


@contextmanager
def _page_session_profile(
    *,
    profile_dir: Path,
    timeout_ms: int,
) -> Iterator[tuple[Any, Any]]:
    want_headless = _headless()
    logger.info(
        "geo-web-crawl persistent profile dir=%s headless=%s thread=%s",
        profile_dir,
        want_headless,
        threading.current_thread().name,
    )
    pw_cm, playwright = _start_playwright()
    context = None
    try:
        with _profile_lock(profile_dir):
            context = playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=want_headless,
                locale="zh-CN",
                viewport=_VIEWPORT,
                args=_LAUNCH_ARGS,
            )
            _apply_context_defaults(context, timeout_ms=timeout_ms)
            page = context.pages[0] if context.pages else context.new_page()
            yield page, context
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.debug("persistent context close failed", exc_info=True)
        _stop_playwright(pw_cm)


@contextmanager
def _page_session_ephemeral(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
) -> Iterator[tuple[Any, Any]]:
    """Local smoke only: a fresh Chrome with Playwright storage_state (not production)."""
    want_headless = _headless()
    logger.info("geo-web-crawl ephemeral chrome headless=%s (no account profile)", want_headless)
    pw_cm, playwright = _start_playwright()
    browser = None
    context = None
    try:
        browser = playwright.chromium.launch(headless=want_headless, args=_LAUNCH_ARGS)
        context = browser.new_context(
            storage_state=storage_state or {"cookies": []},
            locale="zh-CN",
            viewport=_VIEWPORT,
        )
        _apply_context_defaults(context, timeout_ms=timeout_ms)
        yield context.new_page(), context
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.debug("ephemeral context close failed", exc_info=True)
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.debug("ephemeral browser close failed", exc_info=True)
        _stop_playwright(pw_cm)


@contextmanager
def page_session(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
    account_id: str = "",
    platform: str = "doubao",
) -> Iterator[tuple[Any, Any]]:
    aid = (account_id or "").strip()
    if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() and not aid:
        raise RuntimeError("account_id required when GEO_CRAWL_PROFILE_ROOT is set")
    if aid:
        from aperix_geo.services.crawl_accounts.profiles import (
            account_profile_dir,
            profile_is_ready,
        )

        profile_dir = account_profile_dir(platform, aid)
        if not profile_is_ready(profile_dir):
            raise RuntimeError(
                f"chrome profile missing for account={aid} dir={profile_dir}; "
                "complete noVNC login first"
            )
        with _page_session_profile(profile_dir=profile_dir, timeout_ms=timeout_ms) as pair:
            yield pair
        return
    with _page_session_ephemeral(
        storage_state=storage_state,
        timeout_ms=timeout_ms,
    ) as pair:
        yield pair
