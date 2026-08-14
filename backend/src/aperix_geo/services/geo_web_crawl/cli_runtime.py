"""Sync Playwright runtime for geo-web-crawl CLI (Docker / host subprocess).

Isolated process path (geo-web-crawl image). Dispatches via platform registry —
same handlers as the resident HTTP service.
"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.geo_web_crawl.result import crawl_fail
from aperix_geo.services.providers.doubao_web.runtime import normalize_doubao_job_mode

logger = logging.getLogger(__name__)


def _default_context_timeout_ms(timeout_s: float) -> int:
    """Playwright default timeout for the context; allow full job budget (cap 15m)."""
    return max(10_000, min(900_000, int(float(timeout_s) * 1000)))


def run_geo_web_cli_job(payload: dict[str, Any], *, mode: str = "crawl") -> dict[str, Any]:
    """Launch Chromium once and run the registered platform handler."""
    from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded, get_handler
    from aperix_geo.services.providers.doubao_web.browser import prepare_sync_playwright_runtime

    ensure_handlers_loaded()
    job_mode = normalize_doubao_job_mode(mode)

    platform = str(payload.get("platform") or "doubao").strip().lower() or "doubao"
    handler = get_handler(platform)
    if handler is None:
        return crawl_fail(
            f"unknown platform: {platform}", error_type="PlatformNotImplemented"
        )

    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return crawl_fail("storage_state missing")

    headless = bool(payload.get("headless", True))
    timeout_s = float(payload.get("timeout_s") or (60 if job_mode == "probe" else 120))
    timeout_ms = _default_context_timeout_ms(timeout_s)
    job_payload = {**payload, "mode": job_mode, "platform": platform}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return crawl_fail(f"playwright is not installed: {exc}")

    prepare_sync_playwright_runtime()
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=headless)
            except Exception as exc:
                logger.exception("sync chromium.launch failed")
                return crawl_fail(
                    f"chromium.launch failed: {type(exc).__name__}: {exc}. "
                    "Use geo-web-crawl Docker or: python -m playwright install chromium"
                )
            context = None
            try:
                context = browser.new_context(
                    storage_state=storage_state,
                    locale="zh-CN",
                    viewport={"width": 1440, "height": 900},
                )
                context.set_default_timeout(max(1_000, timeout_ms))
                try:
                    context.grant_permissions(["clipboard-read", "clipboard-write"])
                except Exception:
                    logger.debug("clipboard permission grant skipped", exc_info=True)
                page = context.new_page()
                logger.info(
                    "geo-web-crawl-cli: sync chromium launched platform=%s mode=%s headless=%s",
                    platform,
                    job_mode,
                    headless,
                )
                from aperix_geo.services.geo_web_crawl.live_view import maybe_attach_live_view

                with maybe_attach_live_view(page, context) as live_meta:
                    result = handler(job_payload, page, context)
                if isinstance(result, dict) and live_meta.get("enabled"):
                    if live_meta.get("live_url"):
                        result["live_url"] = live_meta["live_url"]
                    if live_meta.get("screenshot_dir"):
                        result["live_screenshot_dir"] = live_meta["screenshot_dir"]
                return result
            finally:
                if context is not None:
                    try:
                        context.close()
                    except Exception:
                        logger.debug("context close failed", exc_info=True)
                try:
                    browser.close()
                except Exception:
                    logger.debug("browser close failed", exc_info=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "geo-web-crawl-cli sync session failed platform=%s mode=%s", platform, job_mode
        )
        return crawl_fail(f"{type(exc).__name__}: {exc}", error_type=type(exc).__name__)
