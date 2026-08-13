"""Run Doubao Playwright crawl in a fresh ``spawn`` subprocess.

Celery prefork children inherit a broken asyncio/greenlet state; Sync Playwright's
``__enter__`` then returns without setting ``_playwright``. A spawned interpreter
avoids that class of failures entirely.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
from typing import Any

logger = logging.getLogger(__name__)


def should_spawn_doubao_crawl() -> bool:
    """True under Celery workers, or when DOUBAO_CRAWL_SUBPROCESS=1."""
    if (os.environ.get("DOUBAO_CRAWL_SUBPROCESS") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    if (os.environ.get("DOUBAO_CRAWL_SUBPROCESS") or "").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False
    return bool((os.environ.get("CELERY_WORKER_ROLE") or "").strip())


def _spawn_worker(conn: Any, payload: dict[str, Any]) -> None:
    """Child entry: must not import Playwright before this process starts."""
    try:
        # Avoid parent Celery role forcing odd paths inside the child.
        os.environ.pop("CELERY_WORKER_ROLE", None)
        from aperix_geo.services.providers.doubao_web.browser_crawl_job import (
            run_doubao_browser_crawl_job,
        )

        conn.send(run_doubao_browser_crawl_job(payload))
    except Exception as exc:  # noqa: BLE001
        conn.send(
            {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "human_ops": False,
                "storage_state": None,
            }
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_doubao_crawl_in_spawn(
    payload: dict[str, Any],
    *,
    timeout_s: float,
) -> dict[str, Any]:
    """Execute browser crawl job in a spawn process; return job result dict."""
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_spawn_worker, args=(child_conn, payload), daemon=True)
    logger.info(
        "doubao crawl browser started (spawn) timeout_s=%s headless=%s",
        timeout_s,
        payload.get("headless"),
    )
    proc.start()
    child_conn.close()
    join_timeout = max(60.0, float(timeout_s) + 60.0)
    proc.join(join_timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        parent_conn.close()
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": f"spawn crawl timed out after {join_timeout:.0f}s",
            "human_ops": False,
            "storage_state": None,
        }
    if parent_conn.poll(5):
        try:
            result = parent_conn.recv()
        except Exception as exc:  # noqa: BLE001
            result = {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": f"spawn crawl result recv failed: {exc}",
                "human_ops": False,
                "storage_state": None,
            }
    else:
        result = {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": f"spawn crawl exited without result code={proc.exitcode}",
            "human_ops": False,
            "storage_state": None,
        }
    parent_conn.close()
    if not isinstance(result, dict):
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": f"spawn crawl returned non-dict: {type(result)!r}",
            "human_ops": False,
            "storage_state": None,
        }
    return result
