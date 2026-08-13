"""Isolated Doubao browser crawl job (runs in-process or inside a spawn child)."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)
from aperix_geo.services.providers.doubao_web.extract import (
    clean_assistant_text,
    extract_quoted_queries,
    extract_urls,
    filter_http_urls,
    panel_present,
)

logger = logging.getLogger(__name__)


def settings_from_crawl_payload(payload: dict[str, Any]) -> Settings:
    return Settings(
        doubao_crawl_timeout_s=float(payload.get("timeout_s") or 120),
        doubao_chat_base_url=str(payload.get("chat_base_url") or sel.CHAT_URL),
        doubao_crawl_headless=bool(payload.get("headless", True)),
        doubao_crawl_require_share_url=bool(payload.get("require_share_url", True)),
        doubao_crawl_browser_reuse=False,
    )


def build_crawl_payload(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "storage_state": storage_state,
        "timeout_s": float(settings.doubao_crawl_timeout_s),
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "headless": bool(settings.doubao_crawl_headless),
        "require_share_url": bool(settings.doubao_crawl_require_share_url),
    }


def run_doubao_browser_crawl_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute chat→reply→panel→share; return a JSON-serializable result dict."""
    from aperix_geo.services.providers.doubao_web import crawler as crawl_mod
    from aperix_geo.services.providers.doubao_web.browser import (
        browser_page_session,
        prepare_sync_playwright_runtime,
    )

    prepare_sync_playwright_runtime()
    settings = settings_from_crawl_payload(payload)
    prompt = str(payload.get("prompt") or "").strip()
    storage_state = payload.get("storage_state")
    if not prompt:
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "empty user prompt",
            "human_ops": False,
            "storage_state": None,
        }
    if not isinstance(storage_state, dict):
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "storage_state missing",
            "human_ops": False,
            "storage_state": None,
        }

    timeout_ms = int(settings.doubao_crawl_timeout_s * 1000)
    started = time.monotonic()
    base_url = (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL

    try:
        with browser_page_session(settings, storage_state=storage_state) as (page, context):
            crawl_deadline = time.monotonic() + settings.doubao_crawl_timeout_s
            page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
            crawl_mod._assert_logged_in(page)
            crawl_mod._assert_no_captcha(page)
            crawl_mod._ensure_blank_chat(page, base_url=base_url)
            crawl_mod._fill_and_send(page, prompt)
            crawl_mod._assert_no_captcha(page)
            crawl_mod._wait_generation_done(
                page,
                settings=settings,
                deadline=crawl_deadline,
            )
            crawl_mod._assert_no_captcha(page)

            raw_text = crawl_mod._extract_assistant_text(page, deadline=crawl_deadline)
            panel_text, panel_hrefs = crawl_mod._extract_search_panel(page)
            queries = extract_quoted_queries(panel_text) if panel_present(panel_text) else ()
            text = clean_assistant_text(
                raw_text,
                user_prompt=prompt,
                search_queries=queries,
            )
            if not text.strip():
                raise DoubaoCrawlError("empty assistant reply")

            source_urls = filter_http_urls(list(panel_hrefs) + list(extract_urls(panel_text)))

            share_url = ""
            share_error: Exception | None = None
            try:
                share_url = crawl_mod._capture_share_url(page)
            except Exception as exc:  # noqa: BLE001
                share_error = exc

            if settings.doubao_crawl_require_share_url and not share_url:
                raise DoubaoShareError(
                    f"share_url required but missing: {share_error or 'empty'}"
                ) from share_error

            new_state = context.storage_state()
            latency_ms = int((time.monotonic() - started) * 1000)
            return {
                "ok": True,
                "text": text.strip(),
                "latency_ms": latency_ms,
                "source_urls": list(source_urls),
                "search_queries": list(queries),
                "share_url": share_url,
                "storage_state": new_state,
                "error_type": "",
                "error": "",
                "human_ops": False,
            }
    except DoubaoNeedsHumanOps as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "human_ops": True,
            "storage_state": None,
        }
    except DoubaoCrawlError as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "human_ops": False,
            "storage_state": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao browser crawl job unexpected error")
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "human_ops": False,
            "storage_state": None,
        }
