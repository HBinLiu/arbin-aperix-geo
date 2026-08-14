"""Doubao login probe job (heartbeat): open chat, optional light send, return storage_state."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.session_cookies import (
    cookies_only_storage_state,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web import ui_flow
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.extract import conversation_id_from_url
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_logged_in,
    assert_no_captcha,
    job_error,
    job_ok,
)

logger = logging.getLogger(__name__)

_DEFAULT_PROBE_PROMPT = "你好"


def build_probe_payload(
    *,
    storage_state: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    send_probe = bool(settings.doubao_heartbeat_send_probe)
    # Login-only stays short; light send needs room for blank chat + post-send watch + delete.
    timeout_cap = 90.0 if send_probe else 60.0
    timeout_s = min(timeout_cap, float(settings.doubao_crawl_timeout_s))
    prompt = (settings.doubao_heartbeat_probe_prompt or "").strip() or _DEFAULT_PROBE_PROMPT
    send_wait_s = float(settings.doubao_heartbeat_send_wait_s)
    return {
        "mode": "probe",
        "storage_state": storage_state,
        "timeout_s": timeout_s,
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "headless": bool(settings.doubao_crawl_headless),
        "send_probe": send_probe,
        "probe_prompt": prompt,
        "send_wait_s": send_wait_s,
    }


def _watch_after_send(page: Any, *, wait_s: float) -> None:
    """After send: poll for captcha or a generating signal; do not require a full reply."""
    deadline = time.monotonic() + max(5.0, wait_s)
    while time.monotonic() < deadline:
        assert_no_captcha(page)
        if ui_flow._stop_button_visible(page) or ui_flow._any_streaming_true(page):
            # Generation started without captcha — good enough for heartbeat.
            assert_no_captcha(page)
            return
        try:
            page.wait_for_timeout(400)
        except Exception as exc:
            name = type(exc).__name__
            if "TargetClosed" in name or "closed" in str(exc).lower():
                raise DoubaoCrawlError("page closed during heartbeat send probe") from exc
            raise
    assert_no_captcha(page)


def _cleanup_probe_conversation(page: Any, *, had_conversation: bool) -> None:
    """Always try to remove the probe thread; hard-fail if one existed and still remains."""
    try:
        ui_flow.delete_current_conversation(page, require=had_conversation)
    except DoubaoCrawlError:
        raise
    except Exception as exc:  # noqa: BLE001
        if had_conversation:
            raise DoubaoCrawlError(f"probe conversation cleanup failed: {exc}") from exc
        logger.warning("probe conversation cleanup ignored: %s", exc)


def run_doubao_login_probe_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return job_error(DoubaoCrawlError("storage_state missing"))
    if not storage_state_has_session_cookies(storage_state):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
            human_ops=True,
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 60)
    timeout_ms = min(90_000, int(timeout_s * 1000))
    send_probe = bool(payload.get("send_probe"))
    prompt = str(payload.get("probe_prompt") or _DEFAULT_PROBE_PROMPT).strip() or _DEFAULT_PROBE_PROMPT
    send_wait_s = float(payload.get("send_wait_s") or 20.0)

    probe_conv_id = ""
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        assert_logged_in(page)
        assert_no_captcha(page)
        composer = page.locator("textarea, div[contenteditable='true']")
        if composer.count() == 0:
            raise DoubaoLoginExpired("chat composer not found")

        if send_probe:
            ui_flow._ensure_blank_chat(page, base_url=base_url)
            assert_no_captcha(page)
            ui_flow._fill_and_send(page, prompt)
            assert_no_captcha(page)
            _watch_after_send(page, wait_s=send_wait_s)
            probe_conv_id = conversation_id_from_url(page.url or "")
            _cleanup_probe_conversation(page, had_conversation=bool(probe_conv_id))

        return job_ok(storage_state=cookies_only_storage_state(context.storage_state()))
    except DoubaoNeedsHumanOps as exc:
        # Still scrub the probe thread when possible (captcha may block UI).
        if send_probe:
            try:
                _cleanup_probe_conversation(
                    page,
                    had_conversation=bool(
                        probe_conv_id or conversation_id_from_url(page.url or "")
                    ),
                )
            except Exception:
                logger.warning(
                    "probe cleanup after human_ops failed conv=%s",
                    probe_conv_id or "-",
                    exc_info=True,
                )
        return job_error(exc, human_ops=True)
    except DoubaoCrawlError as exc:
        if send_probe and (probe_conv_id or conversation_id_from_url(getattr(page, "url", "") or "")):
            try:
                _cleanup_probe_conversation(page, had_conversation=True)
            except Exception:
                logger.warning("probe cleanup after error failed", exc_info=True)
        return job_error(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao login probe unexpected error")
        if send_probe:
            try:
                _cleanup_probe_conversation(
                    page,
                    had_conversation=bool(
                        probe_conv_id or conversation_id_from_url(getattr(page, "url", "") or "")
                    ),
                )
            except Exception:
                logger.warning("probe cleanup after unexpected error failed", exc_info=True)
        return job_error(exc)
