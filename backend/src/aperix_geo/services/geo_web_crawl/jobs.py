"""Execute one geo-web-crawl job on a worker thread."""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aperix_geo.services.geo_web_crawl import browser_pool
from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded, get_handler
from aperix_geo.services.geo_web_crawl.result import context_timeout_ms, crawl_fail

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _concurrency() -> int:
    try:
        return max(1, min(16, int(os.environ.get("GEO_WEB_CRAWL_CONCURRENCY") or "1")))
    except ValueError:
        return 1


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


def _run_job_sync(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_handlers_loaded()
    try:
        account_id, storage_state, platform = browser_pool.parse_job_session(payload)
    except ValueError as exc:
        return crawl_fail(str(exc))

    handler = get_handler(platform)
    if handler is None:
        return crawl_fail(
            f"unknown platform: {platform}",
            error_type="PlatformNotImplemented",
        )

    timeout_s = float(payload.get("timeout_s") or 120)
    timeout_ms = context_timeout_ms(timeout_s)

    try:
        with browser_pool.page_session(
            storage_state=storage_state,
            timeout_ms=timeout_ms,
            account_id=account_id,
            platform=platform,
        ) as (page, context):
            return handler(payload, page, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception("geo-web-crawl job failed platform=%s", platform)
        return crawl_fail(f"{type(exc).__name__}: {exc}", error_type=type(exc).__name__)


def submit_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Run job on the crawl thread pool (blocking)."""
    fut = get_executor().submit(_run_job_sync, payload)
    timeout_s = float(payload.get("timeout_s") or 120) + 60.0
    try:
        return fut.result(timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001
        return crawl_fail(f"job wait failed: {type(exc).__name__}: {exc}")
