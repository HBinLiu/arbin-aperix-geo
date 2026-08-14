"""Tests for geo-web-crawl live view helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from aperix_geo.services.geo_web_crawl.live_view import (
    live_view_enabled,
    rewrite_live_url,
    try_start_browserless_live_url,
)


def test_live_view_enabled(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_LIVE_VIEW", raising=False)
    assert live_view_enabled() is False
    monkeypatch.setenv("GEO_WEB_CRAWL_LIVE_VIEW", "1")
    assert live_view_enabled() is True


def test_rewrite_live_url(monkeypatch) -> None:
    monkeypatch.setenv("GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL", "http://127.0.0.1:3001")
    out = rewrite_live_url("http://browserless:3000/live/index.html?i=abc")
    assert out.startswith("http://127.0.0.1:3001/live/")
    assert "i=abc" in out


def test_try_start_live_url_ok() -> None:
    page = MagicMock()
    context = MagicMock()
    cdp = MagicMock()
    cdp.send.return_value = {"liveURL": "http://browserless:3000/live/index.html?i=x"}
    context.new_cdp_session.return_value = cdp
    url = try_start_browserless_live_url(page, context)
    assert url and "live" in url
    cdp.send.assert_called_once()
    assert cdp.send.call_args[0][0] == "Browserless.liveURL"


def test_try_start_live_url_missing_command() -> None:
    page = MagicMock()
    context = MagicMock()
    cdp = MagicMock()
    cdp.send.side_effect = Exception("Unknown method")
    context.new_cdp_session.return_value = cdp
    assert try_start_browserless_live_url(page, context) is None
