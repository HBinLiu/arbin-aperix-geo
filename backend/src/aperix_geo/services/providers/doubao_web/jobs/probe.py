"""Doubao login probe job (heartbeat): real login proof via short send + delete."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.cookies import (
    job_payload_storage_state,
    job_requires_injected_session_cookies,
    storage_state_from_context,
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
    wait_until_logged_in,
)

logger = logging.getLogger(__name__)

_DEFAULT_PROBE_PROMPT = "你好"


def build_probe_payload(
    *,
    storage_state: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    # Heartbeat must prove a real session: always light-send.
    timeout_s = min(90.0, float(settings.doubao_crawl_timeout_s))
    prompt = (settings.doubao_heartbeat_probe_prompt or "").strip() or _DEFAULT_PROBE_PROMPT
    return {
        "mode": "probe",
        "storage_state": storage_state,
        "timeout_s": timeout_s,
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "probe_prompt": prompt,
        "send_wait_s": float(settings.doubao_heartbeat_send_wait_s),
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


def _try_cleanup_probe_after_failure(page: Any, *, probe_conv_id: str) -> None:
    if not (probe_conv_id or conversation_id_from_url(getattr(page, "url", "") or "")):
        return
    try:
        _cleanup_probe_conversation(page, had_conversation=True)
    except Exception:
        logger.warning("probe cleanup after failure failed", exc_info=True)


def _final_storage_state(
    context: Any,
    *,
    fallback: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    state = storage_state_from_context(context, fallback=fallback, log_event="probe")
    if storage_state_has_session_cookies(state):
        return state
    if not job_requires_injected_session_cookies(payload):
        return state
    raise DoubaoLoginExpired(
        "probe finished but storage_state lost Doubao session cookies"
    )


def run_doubao_login_probe_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Real heartbeat: login UI check → short send → generation → delete → cookie jar.

    Success means Doubao accepted a message on this session. Guest / from_logout /
    send-no-op must fail as DoubaoLoginExpired / DoubaoCrawlError (human_ops).
    """
    storage_state = job_payload_storage_state(payload)
    if storage_state is None:
        return job_error(DoubaoCrawlError("storage_state missing"))
    if job_requires_injected_session_cookies(payload) and not storage_state_has_session_cookies(
        storage_state
    ):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 90)
    timeout_ms = min(90_000, int(timeout_s * 1000))
    prompt = str(payload.get("probe_prompt") or _DEFAULT_PROBE_PROMPT).strip() or _DEFAULT_PROBE_PROMPT
    send_wait_s = float(payload.get("send_wait_s") or 20.0)

    probe_conv_id = ""
    seen_login = False
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        wait_until_logged_in(page, base_url=base_url)
        seen_login = True
        assert_no_captcha(page)

        ui_flow.ensure_blank_chat(page, base_url=base_url)
        assert_logged_in(page)
        assert_no_captcha(page)

        prior_conv = conversation_id_from_url(page.url or "")
        ui_flow._fill_and_send(page, prompt, base_url=base_url)
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

        return job_ok(storage_state=_final_storage_state(context, fallback=storage_state, payload=payload))
    except DoubaoNeedsHumanOps as exc:
        _try_cleanup_probe_after_failure(page, probe_conv_id=probe_conv_id)
        return job_error(exc, session_alive=seen_login)
    except DoubaoCrawlError as exc:
        _try_cleanup_probe_after_failure(page, probe_conv_id=probe_conv_id)
        return job_error(exc, session_alive=seen_login)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao login probe unexpected error")
        _try_cleanup_probe_after_failure(page, probe_conv_id=probe_conv_id)
        return job_error(exc, session_alive=seen_login)
