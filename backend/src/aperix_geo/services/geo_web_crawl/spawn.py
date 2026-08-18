"""Run geo-web-crawl jobs: resident HTTP service, else local CLI subprocess.

Production: ``GEO_WEB_CRAWL_BASE_URL`` → long-running geo-web-crawl service.
Dev fallback: host ``geo_web_crawl.cli`` subprocess.
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

from aperix_geo.services.geo_web_crawl.result import crawl_fail

logger = logging.getLogger(__name__)

_MODULE = "aperix_geo.services.geo_web_crawl.cli"


def _read_result(out_path: Path, *, returncode: int, stderr: str, stdout: str) -> dict[str, Any]:
    if not out_path.is_file():
        err_tail = (stderr or stdout or "").strip()[-800:]
        return crawl_fail(f"crawl missing output file exit={returncode}: {err_tail}")
    try:
        result = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return crawl_fail(f"crawl invalid output JSON: {exc}")
    if not isinstance(result, dict):
        return crawl_fail(f"crawl returned non-dict: {type(result)!r}")
    if not result.get("ok"):
        logger.warning(
            "geo-web-crawl-child result ok=false type=%s err=%s exit=%s",
            result.get("error_type"),
            str(result.get("error") or "")[:400],
            returncode,
        )
    return result


def _log_child_output(*, stderr: str, stdout: str, returncode: int) -> None:
    if stderr:
        for line in stderr.strip().splitlines()[-40:]:
            logger.info("geo-web-crawl-child: %s", line)
    if returncode != 0 and stdout:
        for line in stdout.strip().splitlines()[-20:]:
            logger.info("geo-web-crawl-child-stdout: %s", line)


def _run_local_subprocess(
    payload: dict[str, Any],
    *,
    join_timeout: float,
    mode: str = "crawl",
) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("CELERY_WORKER_ROLE", None)

    with tempfile.TemporaryDirectory(prefix="geo-web-crawl-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            _MODULE,
            "--mode",
            mode,
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
            return crawl_fail(f"subprocess crawl timed out after {join_timeout:.0f}s")
        except Exception as exc:  # noqa: BLE001
            return crawl_fail(f"subprocess crawl failed to start: {exc}")

        _log_child_output(
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
            returncode=completed.returncode,
        )
        return _read_result(
            out_path,
            returncode=completed.returncode,
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
        )


def run_geo_web_crawl_spawn(
    payload: dict[str, Any],
    *,
    timeout_s: float,
    mode: str = "crawl",
    base_url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Run crawl/probe/sign/http/share via resident HTTP, else local CLI."""
    from aperix_geo.services.providers.doubao_web.runtime import normalize_doubao_job_mode

    join_timeout = max(60.0, float(timeout_s) + 60.0)
    job_mode = normalize_doubao_job_mode(mode)
    payload = {
        **payload,
        "mode": job_mode,
        "platform": str(payload.get("platform") or "doubao").strip().lower() or "doubao",
        "timeout_s": float(payload.get("timeout_s") or timeout_s),
    }

    from aperix_geo.services.geo_web_crawl.client import (
        resolve_geo_web_crawl_base_url,
        run_geo_web_crawl_job,
    )

    url = resolve_geo_web_crawl_base_url(base_url)
    if url:
        return run_geo_web_crawl_job(
            payload,
            base_url=url,
            token=token,
            timeout_s=float(timeout_s),
        )

    logger.warning(
        "geo web crawl: GEO_WEB_CRAWL_BASE_URL unset; "
        "using host geo_web_crawl.cli subprocess. mode=%s timeout_s=%s",
        job_mode,
        timeout_s,
    )
    return _run_local_subprocess(payload, join_timeout=join_timeout, mode=job_mode)
