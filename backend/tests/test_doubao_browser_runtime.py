"""Tests for Sync Playwright runtime prepare + async greenlet bridge."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from aperix_geo.services.providers.doubao_web import browser as bp
from aperix_geo.services.providers.doubao_web.browser_crawl_async import (
    _AsyncHub,
    _proxy,
    run_doubao_browser_crawl_on_async_page,
)


def test_prepare_clears_preinstalled_idle_loop() -> None:
    import asyncio as aio

    idle = aio.new_event_loop()
    aio.set_event_loop(idle)
    try:
        bp.prepare_sync_playwright_runtime()
        # set_event_loop(None) — Playwright Sync must create its own loop on enter.
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


def test_async_bridge_proxy_awaits_coroutines() -> None:
    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/"

        async def goto(self, url: str, **_kwargs: object) -> str:
            await asyncio.sleep(0)
            self.url = url
            return url

        def locator(self, _sel: str) -> FakeLocator:
            return FakeLocator()

    class FakeLocator:
        async def count(self) -> int:
            await asyncio.sleep(0)
            return 2

    async def _run() -> None:
        hub = _AsyncHub(asyncio.get_running_loop())
        page = _proxy(FakePage(), hub)
        box: dict[str, object] = {}

        def worker() -> None:
            page.goto("https://doubao.com/chat/")
            box["n"] = page.locator("x").count()
            box["url"] = page.url

        import greenlet

        fiber = greenlet.greenlet(worker)
        fiber.switch()
        while not fiber.dead:
            await asyncio.sleep(0)
            if not fiber.dead:
                fiber.switch()

        assert box["n"] == 2
        assert box["url"] == "https://doubao.com/chat/"

    asyncio.run(_run())


def test_async_bridge_invokes_sync_on_page(monkeypatch) -> None:
    calls: list[tuple[object, object]] = []

    def fake_on_page(page: object, context: object, payload: dict) -> dict:
        calls.append((page, context))
        return {
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
        }

    monkeypatch.setattr(
        "aperix_geo.services.providers.doubao_web.browser_crawl_job.run_doubao_browser_crawl_on_page",
        fake_on_page,
    )

    async def _run() -> dict:
        page = MagicMock()
        context = MagicMock()

        async def _goto(*_a, **_k):
            return None

        page.goto = _goto
        return await run_doubao_browser_crawl_on_async_page(
            page, context, {"prompt": "x", "storage_state": {"cookies": []}}
        )

    result = asyncio.run(_run())
    assert result["ok"] is True
    assert len(calls) == 1
