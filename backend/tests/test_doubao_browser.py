"""Tests for Doubao sync browser one-shot sessions (heartbeat path)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web import browser as bp


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_crawl_headless": True,
        "doubao_crawl_timeout_s": 120,
    }
    base.update(kwargs)
    return Settings(**base)


def _pw_cm(playwright: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = playwright
    cm.__exit__.return_value = False
    cm._playwright = playwright
    cm._connection = MagicMock()
    return cm


def test_oneshot_launches_each_session() -> None:
    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    context.new_page.return_value = page
    browser.new_context.return_value = context
    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser

    with patch("playwright.sync_api.sync_playwright", return_value=_pw_cm(playwright)):
        with bp.browser_page_session(_settings(), storage_state={"cookies": []}) as (p1, c1):
            assert p1 is page
            assert c1 is context
        with bp.browser_page_session(_settings(), storage_state={"cookies": []}):
            pass

    assert playwright.chromium.launch.call_count == 2
    assert browser.close.call_count == 2
    assert context.close.call_count == 2
