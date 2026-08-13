"""Execute one geo-web-crawl job on a worker thread with a warm browser."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aperix_geo.services.geo_web_crawl import browser_pool
from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded, get_handler

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None
_executor_lock = __import__("threading").Lock()


def _concurrency() -> int:
    try:
        return max(1, min(16, int(os.environ.get("GEO_WEB_CRAWL_CONCURRENCY") or "2")))
    except ValueError:
        return 2


def get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            size = _concurrency()
            _executor = ThreadPoolExecutor(
                max_workers=size,
                thread_name_prefix="geo-web-crawl",
            )
            logger.info("geo-web-crawl: thread pool size=%s", size)
        return _executor


def shutdown_executor() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None
    browser_pool.shutdown_all_browsers()


def _fail(message: str, *, error_type: str = "DoubaoCrawlError") -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": error_type,
        "error": message,
        "human_ops": False,
        "storage_state": None,
    }


def _run_job_sync(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_handlers_loaded()
    platform = str(payload.get("platform") or "doubao").strip().lower() or "doubao"
    handler = get_handler(platform)
    if handler is None:
        return _fail(
            f"unknown platform: {platform}",
            error_type="PlatformNotImplemented",
        )

    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return _fail("storage_state missing")

    timeout_s = float(payload.get("timeout_s") or 120)
    timeout_ms = min(60_000, int(timeout_s * 1000))
    headless = payload.get("headless")
    headless_b = None if headless is None else bool(headless)

    try:
        with browser_pool.page_session(
            storage_state=storage_state,
            timeout_ms=timeout_ms,
            headless=headless_b,
        ) as (page, context):
            return handler(payload, page, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception("geo-web-crawl job failed platform=%s", platform)
        return _fail(f"{type(exc).__name__}: {exc}", error_type=type(exc).__name__)


def submit_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Run job on the crawl thread pool (blocking)."""
    fut = get_executor().submit(_run_job_sync, payload)
    timeout_s = float(payload.get("timeout_s") or 120) + 60.0
    try:
        return fut.result(timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"job wait failed: {type(exc).__name__}: {exc}")
