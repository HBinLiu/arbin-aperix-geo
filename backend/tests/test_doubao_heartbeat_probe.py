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


def test_build_probe_payload() -> None:
    settings = Settings(doubao_crawl_timeout_s=120, doubao_crawl_headless=True)
    payload = build_probe_payload(storage_state=_session_state(), settings=settings)
    assert payload["mode"] == "probe"
    assert payload["timeout_s"] == 90.0  # send_probe default True → 90s cap
    assert payload["send_probe"] is True
    assert payload["probe_prompt"] == "你好"
    assert payload["storage_state"]["cookies"]


def test_build_probe_payload_login_only() -> None:
    settings = Settings(
        doubao_crawl_timeout_s=120,
        doubao_heartbeat_send_probe=False,
    )
    payload = build_probe_payload(storage_state=_session_state(), settings=settings)
    assert payload["send_probe"] is False
    assert payload["timeout_s"] == 60.0


def test_probe_on_page_login_redirect() -> None:
    class Page:
        url = "https://www.doubao.com/passport/login"

        def goto(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return {}

    out = run_doubao_login_probe_on_page(
        Page(), Ctx(), {"storage_state": _session_state(), "timeout_s": 30, "send_probe": False}
    )
    assert out["ok"] is False
    assert out["error_type"] == "DoubaoLoginExpired"
    assert out["human_ops"] is True


def test_probe_on_page_send_detects_captcha() -> None:
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCaptchaRequired

    class Loc:
        def count(self):
            return 1

    class Page:
        url = "https://www.doubao.com/chat/"

        def goto(self, *_a, **_k):
            return None

        def locator(self, *_a, **_k):
            return Loc()

        def wait_for_timeout(self, *_a, **_k):
            return None

    class Ctx:
        def storage_state(self):
            return _session_state()

    checks = {"n": 0}

    def _assert_captcha(_page):
        checks["n"] += 1
        # After fill_and_send: open + blank + post-send asserts.
        if checks["n"] >= 3:
            raise DoubaoCaptchaRequired("behavior captcha after send")

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_logged_in",
            return_value=None,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.assert_no_captcha",
            side_effect=_assert_captcha,
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
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._stop_button_visible",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._any_streaming_true",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow.delete_current_conversation",
            return_value=None,
        ) as delete_conv,
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": _session_state(),
                "timeout_s": 30,
                "send_probe": True,
                "probe_prompt": "你好",
                "send_wait_s": 1,
            },
        )
    assert out["ok"] is False
    assert out["error_type"] == "DoubaoCaptchaRequired"
    assert out["human_ops"] is True
    assert delete_conv.called


def test_probe_on_page_send_deletes_conversation() -> None:
    class Loc:
        def count(self):
            return 1

    class Page:
        url = "https://www.doubao.com/chat/abc123456789"

        def goto(self, *_a, **_k):
            return None

        def locator(self, *_a, **_k):
            return Loc()

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
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._stop_button_visible",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow._any_streaming_true",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.jobs.probe.ui_flow.delete_current_conversation",
            return_value=None,
        ) as delete_conv,
        patch(
            "aperix_geo.services.crawl_accounts.session_cookies.cookies_only_storage_state",
            return_value=_session_state(),
        ),
    ):
        out = run_doubao_login_probe_on_page(
            Page(),
            Ctx(),
            {
                "storage_state": _session_state(),
                "timeout_s": 30,
                "send_probe": True,
                "probe_prompt": "你好",
                "send_wait_s": 1,
            },
        )
    assert out["ok"] is True
    delete_conv.assert_called_once()
    assert delete_conv.call_args.kwargs.get("require") is True


def test_delete_current_conversation_skips_blank_url() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import delete_current_conversation

    class Page:
        url = "https://www.doubao.com/chat/"

    delete_current_conversation(Page(), require=True)


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
        },
    ):
        with pytest.raises(DoubaoCrawlError, match="boom"):
            probe_account_login(_session_state(), settings=settings)


def test_probe_account_login_empty_cookies() -> None:
    with pytest.raises(DoubaoLoginExpired):
        probe_account_login({"cookies": []}, settings=Settings())
