"""Tests for Doubao crawl browser reuse pool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web import browser as bp


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_crawl_headless": True,
        "doubao_crawl_browser_reuse": True,
        "doubao_crawl_timeout_s": 120,
    }
    base.update(kwargs)
    return Settings(**base)


def setup_function() -> None:
    bp.reset_browser_pool()


def teardown_function() -> None:
    bp.reset_browser_pool()


def _pw_cm(playwright: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = playwright
    cm.__exit__.return_value = False
    return cm


def test_reuse_keeps_same_browser_across_sessions() -> None:
    browser = MagicMock()
    browser.is_connected.return_value = True
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
        with bp.browser_page_session(_settings(), storage_state={"cookies": []}) as (p2, c2):
            assert p2 is page

    assert playwright.chromium.launch.call_count == 1
    assert browser.new_context.call_count == 2
    assert context.close.call_count == 2
    browser.close.assert_not_called()


def test_reuse_disabled_launches_each_time() -> None:
    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    context.new_page.return_value = page
    browser.new_context.return_value = context

    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser

    with patch("playwright.sync_api.sync_playwright", return_value=_pw_cm(playwright)):
        with bp.browser_page_session(
            _settings(doubao_crawl_browser_reuse=False),
            storage_state={"cookies": []},
        ):
            pass
        with bp.browser_page_session(
            _settings(doubao_crawl_browser_reuse=False),
            storage_state={"cookies": []},
        ):
            pass

    assert playwright.chromium.launch.call_count == 2
    assert browser.close.call_count == 2


def test_dead_browser_is_relaunched() -> None:
    dead = MagicMock()
    dead.is_connected.return_value = False
    alive = MagicMock()
    alive.is_connected.return_value = True
    context = MagicMock()
    page = MagicMock()
    context.new_page.return_value = page
    alive.new_context.return_value = context

    playwright = MagicMock()
    playwright.chromium.launch.return_value = alive

    with patch("playwright.sync_api.sync_playwright", return_value=_pw_cm(playwright)):
        with bp._LOCK:
            bp._PLAYWRIGHT = MagicMock()
            bp._PW_CM = MagicMock()
            bp._BROWSER = dead
            bp._BROWSER_HEADLESS = True
        with bp.browser_page_session(_settings(), storage_state={"cookies": []}):
            pass

    assert playwright.chromium.launch.call_count == 1
    dead.close.assert_called()
    alive.new_context.assert_called_once()


def test_discard_inherited_clears_refs_without_stop() -> None:
    pw = MagicMock()
    cm = MagicMock()
    browser = MagicMock()
    with bp._LOCK:
        bp._PLAYWRIGHT = pw
        bp._PW_CM = cm
        bp._BROWSER = browser
        bp._BROWSER_HEADLESS = True
    bp.discard_browser_pool_inherited()
    assert bp._PLAYWRIGHT is None
    assert bp._BROWSER is None
    pw.stop.assert_not_called()
    browser.close.assert_not_called()
    cm.__exit__.assert_not_called()
