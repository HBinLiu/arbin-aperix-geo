"""Fetch homepage context for competitor / subject profiling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl.metadata import extract_page_metadata, homepage_metadata_dict, SeoProfile
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.text import truncate_text
from aperix_geo.utils.net import (
    host_from,
    host_resolves,
    parse_url,
    profile_crawl_urls,
    registrable_from,
)

logger = logging.getLogger(__name__)

__all__ = ["HomepageContext", "fetch_site_homepage_context"]


@dataclass(frozen=True)
class HomepageContext:
    """首页抓取结果，供微观利基画像 LLM 使用。"""

    url: str
    metadata: dict[str, str]
    markdown: str


def _dns_reachable(user_url: str, root: str) -> bool:
    hosts: list[str] = []
    normalized = parse_url(user_url)
    if normalized:
        host = urlparse(normalized).hostname
        if host:
            hosts.append(host)
    if root:
        hosts.append(root)
        hosts.append(f"www.{root}")
    for host in hosts:
        reg = registrable_from(host) or host_from(host)
        if host_resolves(host) or host_resolves(f"www.{reg}"):
            return True
    return False


def fetch_site_homepage_context(
    domain: str,
    *,
    user_url: str = "",
    crawl: PageCrawlSettings | None = None,
    max_chars_total: int | None = None,
) -> HomepageContext:
    settings = crawl or page_crawl_settings()
    max_chars = max_chars_total if max_chars_total is not None else settings.max_chars

    raw_input = user_url.strip() or domain.strip()
    root = registrable_from(raw_input) or host_from(domain) or host_from(raw_input)
    if not root and not raw_input:
        return HomepageContext(url="", metadata={}, markdown="")

    if not _dns_reachable(raw_input, root):
        logger.info("竞品发现: 跳过首页抓取，DNS 解析失败 域名=%s", root or raw_input)
        return HomepageContext(url="", metadata={}, markdown="")

    candidates = profile_crawl_urls(raw_input, root=root)

    last_url = candidates[0] if candidates else ""
    for start_url in candidates:
        last_url = start_url
        result = fetch_page(start_url, crawl=settings, max_chars=max_chars)
        parsed = extract_page_metadata(
            html=result.html,
            markdown=result.markdown,
            body_limit=max_chars,
            seo_profile=SeoProfile.SUBJECT_HOMEPAGE,
        )
        body = truncate_text(parsed.body_text, max_chars) if parsed.body_text else ""
        if not body:
            body = parsed.seo_prose(max_chars=max_chars)
        if not result.fetch_ok or not body:
            continue

        page_url = result.final_url or start_url
        meta = homepage_metadata_dict(parsed)
        logger.info(
            "竞品发现: 首页抓取完成 域名=%s url=%s source=%s title=%r 字符数=%d",
            root,
            page_url,
            result.source,
            meta.get("title", "")[:80],
            len(body),
        )
        return HomepageContext(
            url=page_url,
            metadata=meta,
            markdown=body,
        )

    return HomepageContext(url=last_url, metadata={}, markdown="")
