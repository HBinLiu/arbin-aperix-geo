"""Tests for Doubao heartbeat probe via geo-web-crawl spawn."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.heartbeat import probe_account_login
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
)
from aperix_geo.services.providers.doubao_web.jobs.probe import (
    build_probe_payload,
    run_doubao_login_probe_on_page,
)


def _session_state() -> dict:
    return {
        "cookies": [
            {"name": "sessionid", "value": "abc", "domain": ".doubao.com", "path": "/"},
        ]
    }


def test_build_probe_payload_always_sends() -> None:
    settings = Settings(
        doubao_crawl_timeout_s=120,
        doubao_crawl_headless=True,
        doubao_heartbeat_send_probe=False,
    )
    payload = build_probe_payload(storage_state=_session_state(), settings=settings)
    assert payload["mode"] == "probe"
    assert payload["timeout_s"] == 90.0
    assert payload["send_probe"] is True
    assert payload["probe_prompt"] == "你好"
    assert payload["storage_state"]["cookies"]


def test_chat_url_is_logged_out() -> None:
    from aperix_geo.services.providers.doubao_web.runtime import chat_url_is_logged_out

    assert chat_url_is_logged_out("https://www.doubao.com/passport/web/login")
    assert chat_url_is_logged_out("https://www.doubao.com/chat/?from_logout=1")
    assert chat_url_is_logged_out("https://www.doubao.com/login")
    assert not chat_url_is_logged_out("https://www.doubao.com/chat/abc")
    assert not chat_url_is_logged_out("https://www.doubao.com/chat/?utm=login_hint")


def test_probe_on_page_login_redirect() -> None:
    class Page:
        url = "https://www.doubao.com/passport/login"

        def goto(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return {}

    out = run_doubao_login_probe_on_page(
        Page(), Ctx(), {"storage_state": _session_state(), "timeout_s": 30}
    )
    assert out["ok"] is False
    assert out["error_type"] == "DoubaoLoginExpired"
    assert out["human_ops"] is True
    assert out.get("session_alive") is False


def test_probe_on_page_send_detects_captcha() -> None:
    class Page:
        url = "https://www.doubao.com/chat/"

        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return _session_state()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_logged_in",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_no_captcha",
            side_effect=[None, None, DoubaoCaptchaRequired("captcha after send")],
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._ensure_blank_chat",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._fill_and_send",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow.delete_current_conversation",
            return_value=None,
        ),
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": _session_state(),
                "timeout_s": 30,
                "probe_prompt": "你好",
                "send_wait_s": 1,
            },
        )
    assert out["ok"] is False
    assert out["error_type"] == "DoubaoCaptchaRequired"
    assert out["human_ops"] is True
    assert out.get("session_alive") is True


def test_probe_on_page_send_fail_keeps_session_alive() -> None:
    class Page:
        url = "https://www.doubao.com/chat/"

        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return _session_state()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_logged_in",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_no_captcha",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._ensure_blank_chat",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._fill_and_send",
            side_effect=DoubaoCrawlError("page closed during send"),
        ),
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": _session_state(),
                "timeout_s": 30,
                "probe_prompt": "你好",
                "send_wait_s": 1,
            },
        )
    assert out["ok"] is False
    assert out["error_type"] == "DoubaoCrawlError"
    assert out["human_ops"] is False
    assert out["session_alive"] is True


def test_probe_on_page_real_send_success() -> None:
    class Page:
        url = "https://www.doubao.com/chat/abc123456789"

        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return _session_state()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_logged_in",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_no_captcha",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._ensure_blank_chat",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._fill_and_send",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._wait_send_accepted",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe._require_generation_signal",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow.delete_current_conversation",
            return_value=None,
        ) as delete_conv,
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.conversation_id_from_url",
            side_effect=["", "abc123456789", "abc123456789", "abc123456789"],
        ),
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": _session_state(),
                "timeout_s": 30,
                "probe_prompt": "你好",
                "send_wait_s": 5,
            },
        )
    assert out["ok"] is True
    assert out["storage_state"]["cookies"]
    delete_conv.assert_called()
    assert delete_conv.call_args.kwargs.get("require") is True


def test_probe_keeps_injected_cookies_when_export_empty() -> None:
    class Page:
        url = "https://www.doubao.com/chat/abc123456789"

        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return {"cookies": []}

    injected = _session_state()
    with (
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_logged_in",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_no_captcha",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._ensure_blank_chat",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._fill_and_send",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._wait_send_accepted",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe._require_generation_signal",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow.delete_current_conversation",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.conversation_id_from_url",
            side_effect=["", "abc123456789", "abc123456789", "abc123456789"],
        ),
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": injected,
                "timeout_s": 30,
                "probe_prompt": "你好",
                "send_wait_s": 5,
            },
        )
    assert out["ok"] is True
    assert out["storage_state"]["cookies"][0]["name"] == "sessionid"


def test_probe_account_login_uses_spawn_ok() -> None:
    settings = Settings(geo_web_crawl_docker_image="aperix/geo-web-crawl:test")
    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.run_geo_web_crawl_spawn",
        return_value={"ok": True, "storage_state": {"cookies": [{"name": "sessionid"}]}},
    ) as spawn:
        state = probe_account_login(_session_state(), settings=settings)
    assert state["cookies"]
    assert spawn.call_args.kwargs["mode"] == "probe"


def test_probe_account_login_maps_captcha() -> None:
    settings = Settings()
    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.run_geo_web_crawl_spawn",
        return_value={
            "ok": False,
            "error_type": "DoubaoCaptchaRequired",
            "error": "captcha",
            "human_ops": True,
        },
    ):
        with pytest.raises(DoubaoCaptchaRequired):
            probe_account_login(_session_state(), settings=settings)


def test_probe_account_login_maps_generic_error() -> None:
    settings = Settings()
    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.run_geo_web_crawl_spawn",
        return_value={
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "boom",
            "human_ops": False,
            "session_alive": True,
        },
    ):
        with pytest.raises(DoubaoCrawlError, match="boom") as ei:
            probe_account_login(_session_state(), settings=settings)
    assert ei.value.session_alive is True


def test_probe_account_login_generic_error_without_session_alive() -> None:
    settings = Settings()
    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.run_geo_web_crawl_spawn",
        return_value={
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "spawn timeout",
            "human_ops": False,
        },
    ):
        with pytest.raises(DoubaoCrawlError, match="spawn timeout") as ei:
            probe_account_login(_session_state(), settings=settings)
    assert ei.value.session_alive is False


def test_probe_account_login_empty_cookies() -> None:
    with pytest.raises(DoubaoLoginExpired):
        probe_account_login({"cookies": []}, settings=Settings())


def test_delete_current_conversation_skips_blank_url() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import delete_current_conversation

    class Page:
        url = "https://www.doubao.com/chat/"

    delete_current_conversation(Page(), require=True)
