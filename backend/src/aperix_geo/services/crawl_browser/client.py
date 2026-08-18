"""HTTP client for the resident crawl-browser service (plus local CLI fallback)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

from aperix_geo.services.crawl_browser.result import crawl_fail

logger = logging.getLogger(__name__)

_CLI_MODULE = "aperix_geo.services.crawl_browser.cli"


def resolve_crawl_base_url(explicit: str | None = None) -> str:
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip().rstrip("/")
    return (os.environ.get("GEO_WEB_CRAWL_BASE_URL") or "").strip().rstrip("/")


def resolve_crawl_token(explicit: str | None = None) -> str:
    if explicit is not None:
        return str(explicit).strip()
    return (os.environ.get("GEO_WEB_CRAWL_TOKEN") or "").strip()


def _post_job(
    payload: dict[str, Any],
    *,
    base_url: str,
    token: str | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """POST ``/v1/jobs`` to the resident crawl service."""
    job_timeout = float(
        timeout_s
        if timeout_s is not None
        else payload.get("timeout_s")
        or 180
    )
    http_timeout = max(30.0, job_timeout + 90.0)
    auth = resolve_crawl_token(token)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"

    body = dict(payload)
    if "platform" not in body or not body["platform"]:
        body["platform"] = "doubao"
    if "timeout_s" not in body:
        body["timeout_s"] = job_timeout

    endpoint = f"{base_url}/v1/jobs"
    logger.info(
        "crawl-browser client POST %s platform=%s mode=%s",
        endpoint,
        body.get("platform"),
        body.get("mode"),
    )
    try:
        with httpx.Client(timeout=http_timeout) as client:
            resp = client.post(endpoint, json=body, headers=headers)
    except httpx.TimeoutException:
        return crawl_fail(f"crawl-browser request timed out after {http_timeout:.0f}s")
    except Exception as exc:  # noqa: BLE001
        return crawl_fail(f"crawl-browser request failed: {type(exc).__name__}: {exc}")

    if resp.status_code == 401:
        return crawl_fail("crawl-browser auth failed (check GEO_WEB_CRAWL_TOKEN)")
    if resp.status_code >= 400:
        return crawl_fail(
            f"crawl-browser HTTP {resp.status_code}: {(resp.text or '')[:400]}"
        )
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return crawl_fail(f"crawl-browser invalid JSON: {exc}")
    if not isinstance(data, dict):
        return crawl_fail(f"crawl-browser returned non-dict: {type(data)!r}")
    if not data.get("ok"):
        logger.warning(
            "crawl-browser job ok=false type=%s err=%s",
            data.get("error_type"),
            str(data.get("error") or "")[:400],
        )
    return data


def _read_cli_result(
    out_path: Path, *, returncode: int, stderr: str, stdout: str
) -> dict[str, Any]:
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
            "crawl-browser-child result ok=false type=%s err=%s exit=%s",
            result.get("error_type"),
            str(result.get("error") or "")[:400],
            returncode,
        )
    return result


def _run_local_cli(
    payload: dict[str, Any],
    *,
    join_timeout: float,
    mode: str = "crawl",
) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("CELERY_WORKER_ROLE", None)

    with tempfile.TemporaryDirectory(prefix="crawl-browser-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            _CLI_MODULE,
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

        if completed.stderr:
            for line in completed.stderr.strip().splitlines()[-40:]:
                logger.info("crawl-browser-child: %s", line)
        if completed.returncode != 0 and completed.stdout:
            for line in completed.stdout.strip().splitlines()[-20:]:
                logger.info("crawl-browser-child-stdout: %s", line)
        return _read_cli_result(
            out_path,
            returncode=completed.returncode,
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
        )


def run_crawl_job(
    payload: dict[str, Any],
    *,
    timeout_s: float | None = None,
    mode: str = "crawl",
    base_url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Run via resident HTTP when ``GEO_WEB_CRAWL_BASE_URL`` is set, else local CLI."""
    from aperix_geo.services.providers.doubao_web.runtime import normalize_doubao_job_mode

    job_timeout = float(
        timeout_s
        if timeout_s is not None
        else payload.get("timeout_s")
        or 180
    )
    job_mode = normalize_doubao_job_mode(mode or str(payload.get("mode") or "crawl"))
    body = {
        **payload,
        "mode": job_mode,
        "platform": str(payload.get("platform") or "doubao").strip().lower() or "doubao",
        "timeout_s": float(payload.get("timeout_s") or job_timeout),
    }

    url = resolve_crawl_base_url(base_url)
    if url:
        return _post_job(
            body,
            base_url=url,
            token=token,
            timeout_s=job_timeout,
        )

    logger.warning(
        "crawl-browser: GEO_WEB_CRAWL_BASE_URL unset; using host CLI subprocess. "
        "mode=%s timeout_s=%s",
        job_mode,
        job_timeout,
    )
    return _run_local_cli(
        body,
        join_timeout=max(60.0, job_timeout + 60.0),
        mode=job_mode,
    )


class CrawlLoginClientError(RuntimeError):
    """crawl-browser login-session HTTP failure."""


def _crawl_headers(token: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    auth = resolve_crawl_token(token)
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    return headers


def start_crawl_login_session(
    *,
    account_id: str,
    platform: str,
    start_url: str,
    ticket_token: str,
    complete_url: str,
    ttl_min: int,
    reason: str = "login_expired",
    baseline_storage_state: dict[str, Any] | None = None,
    base_url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """POST ``/v1/login-sessions`` so crawl's headed Chrome is the VNC desktop."""
    url_base = resolve_crawl_base_url(base_url)
    if not url_base:
        raise CrawlLoginClientError("GEO_WEB_CRAWL_BASE_URL is not set")
    body = {
        "account_id": str(account_id).strip(),
        "platform": platform or "doubao",
        "start_url": start_url,
        "ticket_token": ticket_token,
        "complete_url": complete_url,
        "ttl_min": int(ttl_min),
        "reason": reason,
        "baseline_storage_state": baseline_storage_state or {},
    }
    endpoint = f"{url_base}/v1/login-sessions"
    logger.info(
        "crawl-browser login start POST %s account=%s reason=%s",
        endpoint,
        body["account_id"],
        reason,
    )
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(endpoint, json=body, headers=_crawl_headers(token))
    except Exception as exc:  # noqa: BLE001
        raise CrawlLoginClientError(f"{type(exc).__name__}: {exc}") from exc
    if resp.status_code >= 400:
        raise CrawlLoginClientError(
            f"HTTP {resp.status_code}: {(resp.text or '')[:400]}"
        )
    data = resp.json()
    if not isinstance(data, dict) or not data.get("ok"):
        raise CrawlLoginClientError(f"unexpected response: {str(data)[:400]}")
    return data


def crawl_login_session_running(
    account_id: str,
    *,
    base_url: str | None = None,
    token: str | None = None,
) -> bool:
    url_base = resolve_crawl_base_url(base_url)
    aid = str(account_id or "").strip()
    if not url_base or not aid:
        return False
    endpoint = f"{url_base}/v1/login-sessions/{aid}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(endpoint, headers=_crawl_headers(token))
    except Exception:
        logger.debug("crawl-browser login status failed account=%s", aid, exc_info=True)
        return False
    if resp.status_code >= 400:
        return False
    try:
        data = resp.json()
    except Exception:
        return False
    return bool(isinstance(data, dict) and data.get("watching"))


def stop_crawl_login_session(
    account_id: str,
    *,
    base_url: str | None = None,
    token: str | None = None,
) -> None:
    url_base = resolve_crawl_base_url(base_url)
    aid = str(account_id or "").strip()
    if not url_base or not aid:
        return
    endpoint = f"{url_base}/v1/login-sessions/stop"
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                endpoint,
                json={"account_id": aid},
                headers=_crawl_headers(token),
            )
        if resp.status_code >= 400:
            logger.warning(
                "crawl-browser login stop HTTP %s: %s",
                resp.status_code,
                (resp.text or "")[:300],
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("crawl-browser login stop failed: %s", exc)
