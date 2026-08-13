"""HTTP client for the resident geo-web-crawl service."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def resolve_geo_web_crawl_base_url(explicit: str | None = None) -> str:
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip().rstrip("/")
    return (os.environ.get("GEO_WEB_CRAWL_BASE_URL") or "").strip().rstrip("/")


def resolve_geo_web_crawl_token(explicit: str | None = None) -> str:
    if explicit is not None:
        return str(explicit).strip()
    return (os.environ.get("GEO_WEB_CRAWL_TOKEN") or "").strip()


def _fail(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": "DoubaoCrawlError",
        "error": message,
        "human_ops": False,
        "storage_state": None,
    }


def run_geo_web_crawl_job(
    payload: dict[str, Any],
    *,
    base_url: str | None = None,
    token: str | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """POST ``/v1/jobs`` to the resident crawl service; return result dict."""
    url_base = resolve_geo_web_crawl_base_url(base_url)
    if not url_base:
        return _fail("GEO_WEB_CRAWL_BASE_URL is not set")

    job_timeout = float(
        timeout_s
        if timeout_s is not None
        else payload.get("timeout_s")
        or os.environ.get("GEO_WEB_CRAWL_TIMEOUT_S")
        or 180
    )
    # HTTP client timeout must exceed job timeout (server holds the request).
    http_timeout = max(30.0, job_timeout + 90.0)
    auth = resolve_geo_web_crawl_token(token)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"

    body = dict(payload)
    if "platform" not in body or not body["platform"]:
        body["platform"] = "doubao"
    if "timeout_s" not in body:
        body["timeout_s"] = job_timeout

    endpoint = f"{url_base}/v1/jobs"
    logger.info(
        "geo-web-crawl client POST %s platform=%s mode=%s",
        endpoint,
        body.get("platform"),
        body.get("mode"),
    )
    try:
        with httpx.Client(timeout=http_timeout) as client:
            resp = client.post(endpoint, json=body, headers=headers)
    except httpx.TimeoutException:
        return _fail(f"geo-web-crawl request timed out after {http_timeout:.0f}s")
    except Exception as exc:  # noqa: BLE001
        return _fail(f"geo-web-crawl request failed: {type(exc).__name__}: {exc}")

    if resp.status_code == 401:
        return _fail("geo-web-crawl auth failed (check GEO_WEB_CRAWL_TOKEN)")
    if resp.status_code >= 400:
        return _fail(
            f"geo-web-crawl HTTP {resp.status_code}: {(resp.text or '')[:400]}"
        )
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return _fail(f"geo-web-crawl invalid JSON: {exc}")
    if not isinstance(data, dict):
        return _fail(f"geo-web-crawl returned non-dict: {type(data)!r}")
    return data
