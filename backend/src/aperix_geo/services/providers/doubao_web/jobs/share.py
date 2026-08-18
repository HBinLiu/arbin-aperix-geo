"""Doubao short UI job: open conversation and capture share_url only."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.cookies import (
    storage_state_from_context,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)
from aperix_geo.services.providers.doubao_web.extract import conversation_id_from_url
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_no_captcha,
    job_error,
    job_ok,
    wait_until_logged_in,
)

logger = logging.getLogger(__name__)

_EMPTY = {"share_url": "", "conversation_id": ""}


def build_share_payload(
    *,
    storage_state: dict[str, Any],
    settings: Settings,
    conversation_id: str = "",
) -> dict[str, Any]:
    timeout_s = min(90.0, float(settings.doubao_crawl_timeout_s))
    return {
        "mode": "share",
        "storage_state": storage_state,
        "timeout_s": timeout_s,
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "headless": bool(settings.doubao_crawl_headless),
        "conversation_id": (conversation_id or "").strip(),
    }


def _conversation_url(base_url: str, conversation_id: str) -> str:
    root = base_url.rstrip("/")
    cid = conversation_id.strip()
    if not cid or cid == "0":
        return root + "/"
    if root.endswith("/chat"):
        return f"{root}/{cid}"
    return f"{root.rstrip('/')}/{cid}"


def run_doubao_share_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from aperix_geo.services.providers.doubao_web.ui_flow import try_capture_share_url

    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return job_error(DoubaoCrawlError("storage_state missing"), **_EMPTY)
    if not storage_state_has_session_cookies(storage_state):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
            **_EMPTY,
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    conversation_id = str(payload.get("conversation_id") or "").strip()
    timeout_s = float(payload.get("timeout_s") or 60)
    timeout_ms = min(90_000, int(timeout_s * 1000))
    started = time.monotonic()

    try:
        page.goto(
            _conversation_url(base_url, conversation_id),
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        wait_until_logged_in(page)
        assert_no_captcha(page)
        page.wait_for_timeout(800)

        live_id = conversation_id_from_url(page.url or "") or conversation_id
        if not live_id or live_id == "0":
            raise DoubaoShareError(
                "share job needs conversation_id (open an existing chat URL)"
            )

        share_url = try_capture_share_url(page)
        assert_no_captcha(page)
        if not share_url:
            raise DoubaoShareError("share_url required but missing")

        return job_ok(
            share_url=share_url,
            conversation_id=live_id,
            latency_ms=int((time.monotonic() - started) * 1000),
            storage_state=storage_state_from_context(
                context, fallback=storage_state, log_event="share"
            ),
        )
    except DoubaoNeedsHumanOps as exc:
        return job_error(exc, **_EMPTY)
    except DoubaoCrawlError as exc:
        return job_error(exc, **_EMPTY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao share job unexpected error")
        return job_error(exc, **_EMPTY)
