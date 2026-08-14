"""Doubao login probe job (heartbeat): open chat, check session, return storage_state."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha
from aperix_geo.services.crawl_accounts.session_cookies import storage_state_has_session_cookies

logger = logging.getLogger(__name__)


def build_probe_payload(
    *,
    storage_state: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    timeout_s = min(60.0, float(settings.doubao_crawl_timeout_s))
    return {
        "mode": "probe",
        "storage_state": storage_state,
        "timeout_s": timeout_s,
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "headless": bool(settings.doubao_crawl_headless),
    }


def _job_error(exc: BaseException, *, human_ops: bool = False) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "human_ops": human_ops,
        "storage_state": None,
    }


def run_doubao_login_probe_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Sync probe on an open Playwright page (geo-web-crawl CLI)."""
    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return _job_error(DoubaoCrawlError("storage_state missing"))
    if not storage_state_has_session_cookies(storage_state):
        return _job_error(DoubaoLoginExpired("storage_state missing Doubao session cookies"), human_ops=True)

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 60)
    timeout_ms = min(60_000, int(timeout_s * 1000))

    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        url = (page.url or "").lower()
        if "login" in url or "passport" in url:
            raise DoubaoLoginExpired(f"redirected to login: {page.url}")
        try:
            body = page.locator("body").inner_text(timeout=3_000) or ""
        except Exception:
            body = ""
        if page_looks_like_captcha(body):
            raise DoubaoCaptchaRequired("behavior captcha on heartbeat probe")
        for css in sel.CAPTCHA_DOM_SELECTORS:
            try:
                loc = page.locator(css)
                if loc.count() > 0 and loc.first.is_visible():
                    raise DoubaoCaptchaRequired("behavior captcha on heartbeat probe")
            except DoubaoCaptchaRequired:
                raise
            except Exception:
                continue
        login_btn = page.get_by_role("button", name=sel.LOGIN_HINT)
        composer = page.locator("textarea, div[contenteditable='true']")
        if login_btn.count() > 0 and composer.count() == 0:
            raise DoubaoLoginExpired("login UI visible")
        if composer.count() == 0:
            raise DoubaoLoginExpired("chat composer not found")
        from aperix_geo.services.crawl_accounts.session_cookies import (
            cookies_only_storage_state,
        )

        return {
            "ok": True,
            "storage_state": cookies_only_storage_state(context.storage_state()),
            "error_type": "",
            "error": "",
            "human_ops": False,
        }
    except DoubaoNeedsHumanOps as exc:
        return _job_error(exc, human_ops=True)
    except DoubaoCrawlError as exc:
        return _job_error(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao login probe unexpected error")
        return _job_error(exc)
