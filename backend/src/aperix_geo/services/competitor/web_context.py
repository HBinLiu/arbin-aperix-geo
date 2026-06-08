"""Fetch homepage context for competitor / subject profiling."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aperix_geo.services.crawl import PageFetchResult, fetch_page, page_crawl_settings
from aperix_geo.services.crawl._crawl4ai import result_markdown as _result_markdown
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.domains import strip_hostname
from aperix_geo.utils.text import headings_from_markdown, truncate_text
from aperix_geo.utils.url import homepage_urls, host_resolves

logger = logging.getLogger(__name__)

# 兼容旧测试引用
__all__ = ["HomepageContext", "fetch_site_homepage_context", "_result_markdown"]


@dataclass(frozen=True)
class HomepageContext:
    """首页抓取结果，供微观利基画像 LLM 使用。"""

    url: str
    metadata: dict[str, str]
    markdown: str


def _pick_start_url(root: str) -> str:
    urls = homepage_urls(root)
    return urls[0] if urls else f"https://{strip_hostname(root) or root}/"


def _metadata_from_fetch(result: PageFetchResult, *, body: str) -> dict[str, str]:
    from aperix_geo.utils.html import parse_head_from_html

    title = ""
    description = ""
    if result.html:
        title, description = parse_head_from_html(result.html[:120_000])
    h1_h2 = headings_from_markdown(body) if body.startswith("#") else headings_from_markdown(result.markdown)
    if not h1_h2 and result.html:
        from aperix_geo.utils.html import extract_headings_from_html

        parts = extract_headings_from_html(result.html[:120_000])
        h1_h2 = " | ".join(parts[:6])
    if not title and h1_h2:
        title = h1_h2.split(" | ", 1)[0][:200]
    return {
        "title": title[:500],
        "description": description[:2000],
        "h1_h2": h1_h2[:500],
    }


def _body_from_fetch(result: PageFetchResult, *, max_chars: int) -> str:
    if result.markdown.strip():
        return truncate_text(result.markdown, max_chars)
    if result.html:
        from aperix_geo.utils.html import html_to_text

        return truncate_text(html_to_text(result.html, limit=max_chars), max_chars)
    return ""


def fetch_site_homepage_context(
    domain: str,
    *,
    crawl: PageCrawlSettings | None = None,
    max_chars_total: int | None = None,
) -> HomepageContext:
    settings = crawl or page_crawl_settings()
    max_chars = max_chars_total if max_chars_total is not None else settings.max_chars

    root = strip_hostname(domain)
    if not root:
        return HomepageContext(url="", metadata={}, markdown="")

    if not host_resolves(root) and not host_resolves(f"www.{root}"):
        logger.info("竞品发现: 跳过首页抓取，DNS 解析失败 域名=%s", root)
        return HomepageContext(url="", metadata={}, markdown="")

    start_url = _pick_start_url(root)
    result = fetch_page(start_url, crawl=settings, max_chars=max_chars)
    body = _body_from_fetch(result, max_chars=max_chars)
    if not result.fetch_ok or not body:
        return HomepageContext(url=start_url, metadata={}, markdown="")

    meta = _metadata_from_fetch(result, body=body)
    logger.info(
        "竞品发现: 首页抓取完成 域名=%s source=%s title=%r 字符数=%d",
        root,
        result.source,
        meta.get("title", "")[:80],
        len(body),
    )
    return HomepageContext(
        url=result.final_url or start_url,
        metadata=meta,
        markdown=body,
    )
