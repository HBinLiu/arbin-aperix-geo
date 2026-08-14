"""Optional live debugging for geo-web-crawl Browserless sessions.

Enable with ``GEO_WEB_CRAWL_LIVE_VIEW=1`` (crawl container).

1. Prefer Browserless CDP ``Browserless.liveURL`` (view-only stream link).
2. If that fails (common on open-source images without Hybrid), fall back to
   periodic screenshots under ``GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR``.
3. Optional ``GEO_WEB_CRAWL_LIVE_VIEW_PAUSE_S`` sleeps after the link is logged
   so you can open it before automation races ahead.

Rewrite internal Docker hosts with ``GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL``
(e.g. ``http://127.0.0.1:3001``) when Browserless is published to the host.
"""

from __future__ import annotations

import logging
import os
import threading
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
            "use screenshots / Debugger instead",
            type(exc).__name__,
        )
        return None
    if not isinstance(result, dict):
        return None
    raw = str(result.get("liveURL") or result.get("liveUrl") or "").strip()
    if not raw:
        return None
    return rewrite_live_url(raw)


def _screenshot_loop(
    page: Any,
    directory: Path,
    stop: threading.Event,
    *,
    interval_s: float,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    idx = 0
    while not stop.wait(timeout=max(1.0, interval_s)):
        idx += 1
        path = directory / f"frame-{idx:04d}.png"
        try:
            page.screenshot(path=str(path), full_page=False)
            logger.info("live view screenshot → %s url=%s", path, getattr(page, "url", ""))
        except Exception as exc:
            logger.info("live view screenshot stopped: %s", exc)
            break


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
    stop = threading.Event()
    thread: threading.Thread | None = None
    if shot_dir is not None:
        meta["screenshot_dir"] = str(shot_dir)
        try:
            interval = float(os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_S") or "5")
        except ValueError:
            interval = 5.0
        thread = threading.Thread(
            target=_screenshot_loop,
            args=(page, shot_dir, stop),
            kwargs={"interval_s": interval},
            name="geo-web-crawl-live-shot",
            daemon=True,
        )
        thread.start()
        logger.warning(
            "geo-web-crawl LIVE VIEW screenshots → %s (every %.0fs)",
            shot_dir,
            max(1.0, interval),
        )

    if not live_url and shot_dir is None:
        logger.warning(
            "geo-web-crawl LIVE VIEW enabled but no liveURL and no "
            "GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR; map Browserless port and "
            "open the container Debugger, or set a screenshot dir"
        )

    pause = live_view_pause_s()
    if pause > 0:
        logger.warning(
            "geo-web-crawl LIVE VIEW pause %.0fs — open the link/Debugger now",
            pause,
        )
        time.sleep(pause)

    try:
        yield meta
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=2.0)
