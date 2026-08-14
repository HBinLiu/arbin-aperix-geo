"""Optional live debugging for geo-web-crawl Browserless sessions.

Enable with ``GEO_WEB_CRAWL_LIVE_VIEW=1`` (crawl container).

1. Prefer Browserless CDP ``Browserless.liveURL`` (view-only stream link).
2. If that fails (common on open-source images without Hybrid), fall back to
   **main-thread** screenshots under ``GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR``
   (start + end only — Sync Playwright is not thread-safe; never shot from a
   background thread).
3. Optional ``GEO_WEB_CRAWL_LIVE_VIEW_PAUSE_S`` sleeps after the link is logged
   so you can open Debugger / liveURL before automation races ahead.

Rewrite internal Docker hosts with ``GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL``
(e.g. ``http://127.0.0.1:3001``) when Browserless is published to the host.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def live_view_enabled() -> bool:
    raw = (os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def live_view_pause_s() -> float:
    try:
        return max(0.0, float(os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW_PAUSE_S") or "0"))
    except ValueError:
        return 0.0


def live_view_screenshot_dir() -> Path | None:
    raw = (os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR") or "").strip()
    if not raw:
        return None
    return Path(raw)


def rewrite_live_url(url: str) -> str:
    """Replace scheme/host of liveURL with public base (host-mapped Browserless)."""
    base = (os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL") or "").strip().rstrip("/")
    if not base or not (url or "").strip():
        return (url or "").strip()
    try:
        src = urlparse(url)
        dst = urlparse(base if "://" in base else f"http://{base}")
        return urlunparse(
            (
                dst.scheme or src.scheme or "http",
                dst.netloc or src.netloc,
                src.path,
                src.params,
                src.query,
                src.fragment,
            )
        )
    except Exception:
        logger.debug("live URL rewrite failed", exc_info=True)
        return url


def try_start_browserless_live_url(page: Any, context: Any) -> str | None:
    """Best-effort Browserless Hybrid liveURL (may be unavailable on OSS images)."""
    try:
        cdp = context.new_cdp_session(page)
    except Exception:
        logger.debug("live view: new_cdp_session failed", exc_info=True)
        return None
    try:
        result = cdp.send(
            "Browserless.liveURL",
            {
                "timeout": 600_000,
                "interactable": False,
                "resizable": False,
            },
        )
    except Exception as exc:
        logger.info(
            "live view: Browserless.liveURL unavailable (%s); "
            "use Debugger / start-end screenshots instead",
            type(exc).__name__,
        )
        return None
    if not isinstance(result, dict):
        return None
    raw = str(result.get("liveURL") or result.get("liveUrl") or "").strip()
    if not raw:
        return None
    return rewrite_live_url(raw)


def _screenshot_once(page: Any, directory: Path, *, label: str) -> None:
    """Capture one frame on the Playwright worker thread only."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{label}.png"
        page.screenshot(path=str(path), full_page=False)
        logger.warning(
            "geo-web-crawl LIVE VIEW screenshot → %s url=%s",
            path,
            getattr(page, "url", ""),
        )
    except Exception:
        logger.info("live view screenshot %s failed", label, exc_info=True)


@contextmanager
def maybe_attach_live_view(page: Any, context: Any) -> Iterator[dict[str, Any]]:
    """Attach live debugging for one page session. Yields meta for job result/logs."""
    meta: dict[str, Any] = {"enabled": False, "live_url": "", "screenshot_dir": ""}
    if not live_view_enabled():
        yield meta
        return

    meta["enabled"] = True
    live_url = try_start_browserless_live_url(page, context)
    if live_url:
        meta["live_url"] = live_url
        logger.warning("geo-web-crawl LIVE VIEW (open in browser): %s", live_url)

    shot_dir = live_view_screenshot_dir()
    if shot_dir is not None:
        meta["screenshot_dir"] = str(shot_dir)
        logger.warning(
            "geo-web-crawl LIVE VIEW screenshots (main thread start/end only) → %s",
            shot_dir,
        )

    if not live_url and shot_dir is None:
        logger.warning(
            "geo-web-crawl LIVE VIEW enabled but no liveURL and no "
            "GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR; open Browserless Debugger at "
            "GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL (default http://127.0.0.1:3001)"
        )

    pause = live_view_pause_s()
    if pause > 0:
        logger.warning(
            "geo-web-crawl LIVE VIEW pause %.0fs — open Debugger / liveURL now",
            pause,
        )
        time.sleep(pause)

    if shot_dir is not None:
        _screenshot_once(page, shot_dir, label="start")

    try:
        yield meta
    finally:
        if shot_dir is not None:
            _screenshot_once(page, shot_dir, label="end")
