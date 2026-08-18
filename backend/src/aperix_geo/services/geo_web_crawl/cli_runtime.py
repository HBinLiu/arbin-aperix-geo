"""Sync Playwright runtime for geo-web-crawl CLI (host subprocess / image entry).

Same handlers as the resident HTTP service.
"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.geo_web_crawl.browser_pool import parse_job_session, page_session
from aperix_geo.services.geo_web_crawl.result import context_timeout_ms, crawl_fail
from aperix_geo.services.providers.doubao_web.runtime import normalize_doubao_job_mode

logger = logging.getLogger(__name__)


def run_geo_web_cli_job(payload: dict[str, Any], *, mode: str = "crawl") -> dict[str, Any]:
    """Launch Chromium once and run the registered platform handler."""
    from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded, get_handler

    ensure_handlers_loaded()
    job_mode = normalize_doubao_job_mode(mode)
    try:
        account_id, storage_state, platform = parse_job_session(payload)
    except ValueError as exc:
        return crawl_fail(str(exc))

    handler = get_handler(platform)
    if handler is None:
        return crawl_fail(
            f"unknown platform: {platform}", error_type="PlatformNotImplemented"
        )

    timeout_s = float(payload.get("timeout_s") or (60 if job_mode == "probe" else 120))
    timeout_ms = context_timeout_ms(timeout_s)
    job_payload = {**payload, "mode": job_mode, "platform": platform}

    try:
        with page_session(
            storage_state=storage_state,
            timeout_ms=timeout_ms,
            account_id=account_id,
            platform=platform,
        ) as (page, context):
            logger.info(
                "geo-web-crawl-cli: session platform=%s mode=%s account=%s",
                platform,
                job_mode,
                account_id or "-",
            )
            return handler(job_payload, page, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "geo-web-crawl-cli sync session failed platform=%s mode=%s", platform, job_mode
        )
        return crawl_fail(f"{type(exc).__name__}: {exc}", error_type=type(exc).__name__)
