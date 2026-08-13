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
from aperix_geo.services.providers.doubao_web.probe_job import (
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
    assert payload["timeout_s"] == 60.0
    assert payload["storage_state"]["cookies"]


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
