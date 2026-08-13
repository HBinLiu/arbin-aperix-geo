"""Run Doubao Playwright crawl in a fresh OS subprocess.

Celery prefork workers are **daemonic** and cannot use ``multiprocessing.Process``
(``daemonic processes are not allowed to have children``). They also inherit a
broken asyncio/greenlet state that breaks Sync Playwright's ``_playwright``.

``subprocess`` + ``python -m ...crawl_cli`` starts a non-daemon interpreter.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MODULE = "aperix_geo.services.providers.doubao_web.crawl_cli"


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


def run_doubao_crawl_in_spawn(
    payload: dict[str, Any],
    *,
    timeout_s: float,
) -> dict[str, Any]:
    """Execute browser crawl job via ``python -m crawl_cli``; return job result dict."""
    join_timeout = max(60.0, float(timeout_s) + 60.0)
    logger.info(
        "doubao crawl browser started (subprocess) timeout_s=%s headless=%s",
        timeout_s,
        payload.get("headless"),
    )

    env = os.environ.copy()
    # Child must not try to spawn again / inherit Celery daemon constraints.
    env.pop("CELERY_WORKER_ROLE", None)
    env["DOUBAO_CRAWL_SUBPROCESS"] = "0"

    with tempfile.TemporaryDirectory(prefix="doubao-crawl-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            _MODULE,
            "--in",
            str(in_path),
            "--out",
            str(out_path),
        ]
        try:
            completed = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=join_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": f"subprocess crawl timed out after {join_timeout:.0f}s",
                "human_ops": False,
                "storage_state": None,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": f"subprocess crawl failed to start: {exc}",
                "human_ops": False,
                "storage_state": None,
            }

        if completed.stderr:
            # Surface child logs for journald without drowning the parent.
            for line in completed.stderr.strip().splitlines()[-30:]:
                logger.info("doubao-crawl-child: %s", line)

        if not out_path.is_file():
            err_tail = (completed.stderr or completed.stdout or "").strip()[-800:]
            return {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": (
                    f"subprocess crawl missing output file exit={completed.returncode}: {err_tail}"
                ),
                "human_ops": False,
                "storage_state": None,
            }

        try:
            result = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": f"subprocess crawl invalid output JSON: {exc}",
                "human_ops": False,
                "storage_state": None,
            }

        if not isinstance(result, dict):
            return {
                "ok": False,
                "error_type": "DoubaoCrawlError",
                "error": f"subprocess crawl returned non-dict: {type(result)!r}",
                "human_ops": False,
                "storage_state": None,
            }
        return result
