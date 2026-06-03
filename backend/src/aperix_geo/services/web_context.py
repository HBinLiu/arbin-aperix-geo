"""Fetch homepage via Crawl4AI for competitor discovery (metadata + Markdown excerpt)."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from aperix_geo.utils.coerce import pick_str
from aperix_geo.utils.domains import strip_hostname
from aperix_geo.utils.text import headings_from_markdown, truncate_text
from aperix_geo.utils.url import homepage_urls, host_resolves

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HomepageContext:
    """首页抓取结果，供微观利基画像 LLM 使用。"""

    url: str
    metadata: dict[str, str]
    markdown: str


def _pick_start_url(root: str) -> str:
    urls = homepage_urls(root)
    return urls[0] if urls else f"https://{strip_hostname(root) or root}/"


def _result_markdown(result: Any) -> str:
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


def _metadata_from_crawl(item: Any, *, markdown: str) -> dict[str, str]:
    raw = getattr(item, "metadata", None)
    title = ""
    description = ""
    if isinstance(raw, dict):
        title = pick_str(raw, "title", "og:title", "twitter:title")
        description = pick_str(
            raw,
            "description",
            "og:description",
            "twitter:description",
        )
    h1_h2 = headings_from_markdown(markdown)
    if not title and h1_h2:
        title = h1_h2.split(" | ", 1)[0][:200]
    return {
        "title": title[:500],
        "description": description[:2000],
        "h1_h2": h1_h2[:500],
    }


async def _fetch_homepage_async(
    domain: str,
    *,
    timeout_s: float,
    max_chars: int,
) -> HomepageContext:
    root = strip_hostname(domain)
    if not root:
        return HomepageContext(url="", metadata={}, markdown="")

    if not host_resolves(root) and not host_resolves(f"www.{root}"):
        logger.info("竞品发现: 跳过首页抓取，DNS 解析失败 域名=%s", root)
        return HomepageContext(url="", metadata={}, markdown="")

    start_url = _pick_start_url(root)
    page_timeout_ms = max(5000, int(timeout_s * 1000))
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        verbose=False,
        page_timeout=page_timeout_ms,
        exclude_external_links=True,
    )

    try:
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
            raw = await asyncio.wait_for(
                crawler.arun(start_url, config=config),
                timeout=timeout_s,
            )
    except asyncio.TimeoutError:
        logger.warning("竞品发现: 首页抓取超时 %s", start_url)
        return HomepageContext(url=start_url, metadata={}, markdown="")
    except Exception:
        logger.warning("竞品发现: 首页抓取失败 %s", start_url, exc_info=True)
        return HomepageContext(url=start_url, metadata={}, markdown="")

    results = raw if isinstance(raw, list) else [raw] if raw is not None else []
    for item in results:
        if not getattr(item, "success", True):
            continue
        md = _result_markdown(item)
        if not md:
            continue
        meta = _metadata_from_crawl(item, markdown=md)
        body = truncate_text(md, max_chars)
        logger.info(
            "竞品发现: 首页抓取完成 域名=%s title=%r 字符数=%d",
            root,
            meta.get("title", "")[:80],
            len(body),
        )
        return HomepageContext(url=start_url, metadata=meta, markdown=body)

    return HomepageContext(url=start_url, metadata={}, markdown="")


def fetch_site_homepage_context(
    domain: str,
    *,
    timeout_s: float = 45.0,
    max_chars_total: int = 14_000,
) -> HomepageContext:
    return asyncio.run(
        _fetch_homepage_async(domain, timeout_s=timeout_s, max_chars=max_chars_total),
    )
