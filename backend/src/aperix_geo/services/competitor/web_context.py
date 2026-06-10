"""Fetch homepage context for competitor / subject profiling."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl._crawl4ai import result_markdown as _result_markdown
from aperix_geo.services.crawl.metadata import extract_page_metadata, homepage_metadata_dict
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.domains import strip_hostname
from aperix_geo.utils.text import truncate_text
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
    parsed = extract_page_metadata(
        html=result.html,
        markdown=result.markdown,
        body_limit=max_chars,
    )
    body = truncate_text(parsed.body_text, max_chars) if parsed.body_text else ""
    if not result.fetch_ok or not body:
        return HomepageContext(url=start_url, metadata={}, markdown="")

    meta = homepage_metadata_dict(parsed)
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
