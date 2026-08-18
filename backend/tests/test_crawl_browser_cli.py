"""Tests for Sync Playwright prepare + geo-web-crawl CLI runtime."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.crawl_browser.jobs import run_job_sync
from aperix_geo.services.providers.doubao_web import browser as bp


def test_prepare_clears_preinstalled_idle_loop() -> None:
    import asyncio as aio

    idle = aio.new_event_loop()
    aio.set_event_loop(idle)
    try:
        bp.prepare_sync_playwright_runtime()
        try:
            current = aio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            current = None
        assert current is not idle
    finally:
        try:
            aio.set_event_loop(None)
        except Exception:
            pass
        if not idle.is_closed():
            idle.close()


def test_cli_runtime_crawl_mode(monkeypatch) -> None:
    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    page = MagicMock()
    context = MagicMock()
    browser = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = page
    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser
    pw_cm = MagicMock()
    pw_cm.start.return_value = playwright

    monkeypatch.setattr(
        "aperix_geo.services.providers.doubao_web.jobs.crawl.run_doubao_browser_crawl_on_page",
        lambda p, c, payload: {
            "ok": True,
            "text": "hi",
            "latency_ms": 1,
            "source_urls": [],
            "search_queries": [],
            "share_url": "",
            "storage_state": {"cookies": []},
            "error_type": "",
            "error": "",
            "human_ops": False,
        },
    )

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        out = run_job_sync(
            {"prompt": "x", "storage_state": {"cookies": []}, "headless": True},
            mode="crawl",
        )
    assert out["ok"] is True
    assert out["text"] == "hi"
    context.close.assert_called()
    browser.close.assert_called()


def test_cli_runtime_probe_mode(monkeypatch) -> None:
    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    page = MagicMock()
    context = MagicMock()
    browser = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = page
    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser
    pw_cm = MagicMock()
    pw_cm.start.return_value = playwright

    monkeypatch.setattr(
        "aperix_geo.services.providers.doubao_web.jobs.probe.run_doubao_login_probe_on_page",
        lambda p, c, payload: {
            "ok": True,
            "storage_state": {"cookies": [{"name": "sessionid"}]},
            "error_type": "",
            "error": "",
            "human_ops": False,
        },
    )

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        out = run_job_sync(
            {"storage_state": {"cookies": [{"name": "sessionid"}]}, "headless": True},
            mode="probe",
        )
    assert out["ok"] is True
    assert out["storage_state"]["cookies"]
    context.close.assert_called()
    browser.close.assert_called()
