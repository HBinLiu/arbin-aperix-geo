"""Doubao login probe job (heartbeat): real login proof via short send + delete."""

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
    # Heartbeat must prove a real session: always light-send (setting only tunes prompt/wait).
    send_probe = True
    timeout_s = min(90.0, float(settings.doubao_crawl_timeout_s))
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
        # Soft flag kept for logs / future; probe ignores false.
        "send_probe_configured": bool(settings.doubao_heartbeat_send_probe),
    }


def _require_generation_signal(page: Any, *, deadline: float) -> None:
    """Require stop/streaming/md-box on a real conversation (not guest chrome)."""
    while time.monotonic() < deadline:
        assert_logged_in(page)
        assert_no_captcha(page)
        conv = conversation_id_from_url(getattr(page, "url", "") or "")
        if not conv:
            page.wait_for_timeout(300)
            continue
        if ui_flow._stop_button_visible(page) or ui_flow._any_streaming_true(page):
            return
        try:
            if page.locator(".md-box-root").count() > 0:
                return
        except Exception:
            pass
        if ui_flow._action_bar_visible(page):
            return
        try:
            page.wait_for_timeout(300)
        except Exception as exc:
            name = type(exc).__name__
            if "TargetClosed" in name or "closed" in str(exc).lower():
                raise DoubaoCrawlError("page closed during heartbeat generation watch") from exc
            raise
    shot = ui_flow._debug_screenshot(page, label="heartbeat-no-generation")
    detail = ui_flow._page_debug_summary(page)
    raise DoubaoCrawlError(
        "heartbeat send produced no generation signal; "
        f"{detail}"
        + (f" shot={shot}" if shot else "")
    )


def _cleanup_probe_conversation(page: Any, *, had_conversation: bool) -> None:
    """Remove the probe thread; hard-fail if one existed and still remains."""
    try:
        ui_flow.delete_current_conversation(page, require=had_conversation)
    except DoubaoCrawlError:
        raise
    except Exception as exc:  # noqa: BLE001
        if had_conversation:
            raise DoubaoCrawlError(f"probe conversation cleanup failed: {exc}") from exc
        logger.warning("probe conversation cleanup ignored: %s", exc)


def _final_storage_state(context: Any) -> dict[str, Any]:
    state = cookies_only_storage_state(context.storage_state())
    if not storage_state_has_session_cookies(state):
        raise DoubaoLoginExpired(
            "probe finished but storage_state lost Doubao session cookies"
        )
    return state


def run_doubao_login_probe_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Real heartbeat: login UI check → short send → generation → delete → cookie jar.

    Success means Doubao accepted a message on this session. Guest / from_logout /
    send-no-op must fail as DoubaoLoginExpired / DoubaoCrawlError (human_ops).
    """
    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return job_error(DoubaoCrawlError("storage_state missing"))
    if not storage_state_has_session_cookies(storage_state):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
            human_ops=True,
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 90)
    timeout_ms = min(90_000, int(timeout_s * 1000))
    prompt = str(payload.get("probe_prompt") or _DEFAULT_PROBE_PROMPT).strip() or _DEFAULT_PROBE_PROMPT
    send_wait_s = float(payload.get("send_wait_s") or 20.0)

    probe_conv_id = ""
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        assert_logged_in(page)
        assert_no_captcha(page)

        ui_flow._ensure_blank_chat(page, base_url=base_url)
        assert_logged_in(page)
        assert_no_captcha(page)

        prior_conv = conversation_id_from_url(page.url or "")
        ui_flow._fill_and_send(page, prompt)
        assert_no_captcha(page)

        deadline = time.monotonic() + max(8.0, send_wait_s)
        # Must open a new thread id — guest pages must not pass.
        ui_flow._wait_send_accepted(
            page,
            prior_conv_id=prior_conv,
            deadline=deadline,
            require_new_conversation=True,
        )
        probe_conv_id = conversation_id_from_url(page.url or "")
        if not probe_conv_id or probe_conv_id == prior_conv:
            raise DoubaoCrawlError(
                f"heartbeat send did not create conversation id (prior={prior_conv or '-'})"
            )

        _require_generation_signal(page, deadline=deadline)
        assert_logged_in(page)
        assert_no_captcha(page)

        _cleanup_probe_conversation(page, had_conversation=True)
        assert_logged_in(page)

        return job_ok(storage_state=_final_storage_state(context))
    except DoubaoNeedsHumanOps as exc:
        if probe_conv_id or conversation_id_from_url(getattr(page, "url", "") or ""):
            try:
                _cleanup_probe_conversation(page, had_conversation=True)
            except Exception:
                logger.warning(
                    "probe cleanup after human_ops failed conv=%s",
                    probe_conv_id or "-",
                    exc_info=True,
                )
        return job_error(exc, human_ops=True)
    except DoubaoCrawlError as exc:
        if probe_conv_id or conversation_id_from_url(getattr(page, "url", "") or ""):
            try:
                _cleanup_probe_conversation(page, had_conversation=True)
            except Exception:
                logger.warning("probe cleanup after error failed", exc_info=True)
        # Treat "could not really chat" as session unusable for ops routing.
        human = isinstance(exc, DoubaoLoginExpired) or "login" in str(exc).lower()
        return job_error(exc, human_ops=human or "from_logout" in str(exc).lower())
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao login probe unexpected error")
        if probe_conv_id:
            try:
                _cleanup_probe_conversation(page, had_conversation=True)
            except Exception:
                logger.warning("probe cleanup after unexpected error failed", exc_info=True)
        return job_error(exc)
