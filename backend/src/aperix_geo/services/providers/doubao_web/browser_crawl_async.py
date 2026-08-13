"""Async Playwright crawl path: drive the sync crawler via a greenlet bridge.

Sync Playwright's greenlet dispatcher is fragile under Celery / dirty asyncio state.
``async_playwright`` is reliable; this module exposes async pages to the existing
sync crawler helpers by switching to the asyncio hub whenever a coroutine appears.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

logger = logging.getLogger(__name__)

_PRIMITIVE = (str, int, float, bool, bytes, type(None))


class _AsyncHub:
    """Pump awaitables from a sync greenlet while the asyncio loop runs in ``main``."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        import greenlet

        self.loop = loop
        self.main = greenlet.getcurrent()

    def call(self, value: Any) -> Any:
        if not inspect.isawaitable(value):
            return value
        task = self.loop.create_task(value)  # type: ignore[arg-type]
        while not task.done():
            self.main.switch()
        exc = task.exception()
        if exc is not None:
            raise exc
        return task.result()


def _proxy(obj: Any, hub: _AsyncHub) -> Any:
    if isinstance(obj, _PRIMITIVE):
        return obj
    if isinstance(obj, (dict, list, tuple, set)):
        return obj
    if isinstance(obj, _Proxy):
        return obj
    return _Proxy(obj, hub)


class _Proxy:
    __slots__ = ("_obj", "_hub")

    def __init__(self, obj: Any, hub: _AsyncHub) -> None:
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_hub", hub)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._obj, name)
        if callable(attr):

            def bound(*args: Any, **kwargs: Any) -> Any:
                raw_args = tuple(
                    a._obj if isinstance(a, _Proxy) else a for a in args  # noqa: SLF001
                )
                raw_kwargs = {
                    k: (v._obj if isinstance(v, _Proxy) else v)  # noqa: SLF001
                    for k, v in kwargs.items()
                }
                result = attr(*raw_args, **raw_kwargs)
                result = self._hub.call(result)
                return _proxy(result, self._hub)

            return bound
        if inspect.isawaitable(attr):
            return _proxy(self._hub.call(attr), self._hub)
        return _proxy(attr, self._hub)

    def __bool__(self) -> bool:
        return bool(self._obj)

    def __repr__(self) -> str:
        return f"_Proxy({self._obj!r})"


async def run_doubao_browser_crawl_on_async_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Run the sync crawl helpers against async Playwright page/context."""
    import greenlet

    from aperix_geo.services.providers.doubao_web.browser_crawl_job import (
        run_doubao_browser_crawl_on_page,
    )

    hub = _AsyncHub(asyncio.get_running_loop())
    sync_page = _proxy(page, hub)
    sync_context = _proxy(context, hub)
    box: dict[str, Any] = {}

    def worker() -> None:
        try:
            box["result"] = run_doubao_browser_crawl_on_page(
                sync_page, sync_context, payload
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("async-bridge sync crawl failed")
            box["result"] = {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "human_ops": False,
                "storage_state": None,
            }

    fiber = greenlet.greenlet(worker)
    fiber.switch()
    while not fiber.dead:
        await asyncio.sleep(0)
        if not fiber.dead:
            fiber.switch()

    result = box.get("result")
    if not isinstance(result, dict):
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "async-bridge produced no result",
            "human_ops": False,
            "storage_state": None,
        }
    return result


async def run_doubao_browser_crawl_job_async(payload: dict[str, Any]) -> dict[str, Any]:
    """Launch Chromium via async_playwright and run the bridged sync crawl."""
    from playwright.async_api import async_playwright

    headless = bool(payload.get("headless", True))
    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        return {
            "ok": False,
            "error_type": "DoubaoCrawlError",
            "error": "storage_state missing",
            "human_ops": False,
            "storage_state": None,
        }

    timeout_s = float(payload.get("timeout_s") or 120)
    timeout_ms = min(60_000, int(timeout_s * 1000))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            context = await browser.new_context(
                storage_state=storage_state,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
            context.set_default_timeout(max(1_000, timeout_ms))
            try:
                await context.grant_permissions(["clipboard-read", "clipboard-write"])
            except Exception:
                logger.debug("clipboard permission grant skipped", exc_info=True)
            page = await context.new_page()
            return await run_doubao_browser_crawl_on_async_page(page, context, payload)
        finally:
            await browser.close()
