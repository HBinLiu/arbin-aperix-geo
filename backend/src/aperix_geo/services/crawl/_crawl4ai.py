"""Crawl4AI helpers (headless browser fallback, shared worker)."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from typing import Any, Literal

logger = logging.getLogger(__name__)


def iter_crawl_results(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if raw is None:
        return []
    return [raw]


def result_markdown(result: Any) -> str:
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    if isinstance(md, str):
        text = md.strip()
    else:
        text = ""
        for attr in ("fit_markdown", "raw_markdown"):
            val = getattr(md, attr, None)
            if val:
                text = str(val).strip()
                break
        if not text:
            text = str(md).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def result_html(result: Any) -> str:
    for attr in ("html", "cleaned_html", "raw_html"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    return ""


class _Crawl4AIWorker:
    """Single background event loop hosting one reused AsyncWebCrawler instance."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._start_lock = threading.Lock()

    def _ensure_started(self) -> asyncio.AbstractEventLoop:
        with self._start_lock:
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run_forever,
                    name="crawl4ai-worker",
                    daemon=True,
                )
                self._thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError("Crawl4AI worker failed to start")
        assert self._loop is not None
        return self._loop

    def _run_forever(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()

    def fetch(
        self,
        url: str,
        *,
        timeout_s: float,
        max_chars: int,
        max_concurrent: int = 5,
    ) -> tuple[str, str, str, Literal["crawl4ai", "none"]]:
        loop = self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(
            self._fetch_async(
                url,
                timeout_s=timeout_s,
                max_chars=max_chars,
                max_concurrent=max_concurrent,
            ),
            loop,
        )
        return future.result(timeout=max(timeout_s + 15.0, 20.0))

    async def _fetch_async(
        self,
        url: str,
        *,
        timeout_s: float,
        max_chars: int,
        max_concurrent: int,
    ) -> tuple[str, str, str, Literal["crawl4ai", "none"]]:
        key = (url or "").strip()
        if not key:
            return "", "", "", "none"

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        except ImportError:
            logger.warning("Crawl4AI 未安装，跳过浏览器兜底抓取")
            return key, "", "", "none"

        if not hasattr(self, "_sem"):
            self._sem = asyncio.Semaphore(max(1, max_concurrent))
        if not hasattr(self, "_crawler"):
            self._crawler = None

        page_timeout_ms = max(5000, int(timeout_s * 1000))
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            check_robots_txt=True,
            verbose=False,
            page_timeout=page_timeout_ms,
            exclude_external_links=True,
        )

        async with self._sem:
            try:
                if self._crawler is None:
                    crawler = AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False))
                    await crawler.__aenter__()
                    self._crawler = crawler
                raw = await asyncio.wait_for(
                    self._crawler.arun(key, config=config),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                logger.warning("Crawl4AI 抓取超时 %s", key)
                return key, "", "", "none"
            except Exception:
                logger.warning("Crawl4AI 抓取失败 %s", key, exc_info=True)
                return key, "", "", "none"

        from aperix_geo.utils.text import truncate_text

        for item in iter_crawl_results(raw):
            if not getattr(item, "success", True):
                continue
            html = truncate_text(result_html(item), max_chars)
            markdown = truncate_text(result_markdown(item), max_chars)
            if not html and not markdown:
                continue
            final_url = str(getattr(item, "url", key) or key)
            return final_url, html, markdown, "crawl4ai"

        return key, "", "", "none"


_worker = _Crawl4AIWorker()


def fetch_url_crawl4ai(
    url: str,
    *,
    timeout_s: float,
    max_chars: int,
    max_concurrent: int = 5,
) -> tuple[str, str, str, Literal["crawl4ai", "none"]]:
    return _worker.fetch(
        url,
        timeout_s=timeout_s,
        max_chars=max_chars,
        max_concurrent=max_concurrent,
    )
