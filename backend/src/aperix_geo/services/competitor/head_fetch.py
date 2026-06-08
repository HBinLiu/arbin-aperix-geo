"""竞品候选站首页：统一 httpx → Crawl4AI 抓取 title / meta description。"""

from __future__ import annotations

import asyncio
import logging

from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.crawl import PageFetchResult, fetch_page, page_crawl_settings
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.html import parse_head_from_html
from aperix_geo.utils.text import headings_from_markdown
from aperix_geo.utils.url import homepage_urls

logger = logging.getLogger(__name__)

_HEAD_PARSE_CHARS = 80_000


def _head_fields(result: PageFetchResult) -> tuple[str, str]:
    title = ""
    description = ""
    if result.html:
        title, description = parse_head_from_html(result.html[:_HEAD_PARSE_CHARS])
    if not title and result.markdown.strip():
        headings = headings_from_markdown(result.markdown)
        if headings:
            title = headings.split(" | ", 1)[0][:200]
    if not title and result.markdown.strip():
        title = result.markdown.strip().split("\n", 1)[0].lstrip("# ").strip()[:200]
    return title, description


def _fetch_one_sync(domain: str, *, crawl: PageCrawlSettings) -> SiteHead:
    urls = homepage_urls(domain)
    if not urls:
        return SiteHead(domain=domain, title="", description="", reachable=False)

    max_chars = min(crawl.max_chars, _HEAD_PARSE_CHARS)
    for url in urls:
        result = fetch_page(url, crawl=crawl, max_chars=max_chars)
        if not result.fetch_ok:
            continue
        title, description = _head_fields(result)
        return SiteHead(
            domain=domain,
            title=title,
            description=description,
            reachable=True,
        )

    return SiteHead(domain=domain, title="", description="", reachable=False)


async def fetch_site_heads_async(
    domains: list[str],
    *,
    concurrency: int | None = None,
) -> dict[str, SiteHead]:
    crawl = page_crawl_settings()
    conc = max(1, concurrency if concurrency is not None else crawl.concurrency)
    unique = dedupe_keys(domains)
    if not unique:
        return {}

    sem = asyncio.Semaphore(conc)
    out: dict[str, SiteHead] = {}

    async def run_one(host: str) -> None:
        async with sem:
            head = await asyncio.to_thread(_fetch_one_sync, host, crawl=crawl)
            out[registrable_domain(head.domain)] = head

    await asyncio.gather(*(run_one(h) for h in unique))

    ok = sum(1 for h in out.values() if h.reachable)
    logger.info("竞品发现: 抓取站点元数据 %d 个，可打开 %d", len(out), ok)
    return out


def fetch_site_heads(
    domains: list[str],
    *,
    concurrency: int | None = None,
) -> dict[str, SiteHead]:
    return asyncio.run(
        fetch_site_heads_async(
            domains,
            concurrency=concurrency,
        ),
    )


def dedupe_keys(domains: list[str]) -> list[str]:
    return list(dict.fromkeys(registrable_domain(d) for d in domains if d.strip()))
