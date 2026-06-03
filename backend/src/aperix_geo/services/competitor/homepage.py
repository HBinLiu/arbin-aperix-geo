"""监测域名站首页：默认轻量 httpx；失败时回退 Crawl4AI。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.defaults import HOMEPAGE_TIMEOUT_S
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.web_context import HomepageContext, fetch_site_homepage_context

logger = logging.getLogger(__name__)


def fetch_target_homepage(domain: str) -> HomepageContext:
    settings = get_settings()
    root = registrable_domain(domain)
    if not root:
        return HomepageContext(url="", metadata={}, markdown="")

    heads = fetch_site_heads([root], timeout_s=HOMEPAGE_TIMEOUT_S, concurrency=1)
    head = heads.get(root)
    if head and head.reachable:
        meta = {
            "title": head.title,
            "description": head.description,
            "h1_h2": "",
        }
        body = head.description or head.title
        logger.info("竞品发现: 监测域名站轻量抓取 %s title=%r", root, meta["title"][:60])
        return HomepageContext(
            url=f"https://{root}/",
            metadata=meta,
            markdown=body[: settings.competitor_target_crawl_max_chars],
        )

    logger.warning("竞品发现: 监测域名站轻量抓取失败，回退 Crawl4AI domain=%s", root)
    return fetch_site_homepage_context(
        root,
        timeout_s=settings.competitor_target_crawl_timeout_s,
        max_chars_total=settings.competitor_target_crawl_max_chars,
    )
