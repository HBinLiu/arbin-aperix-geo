"""监测域名站首页：统一 httpx → Crawl4AI 抓取。"""

from __future__ import annotations

from aperix_geo.services.competitor.web_context import HomepageContext, fetch_site_homepage_context
from aperix_geo.services.crawl import page_crawl_settings
from aperix_geo.utils.domains import registrable_domain


def fetch_target_homepage(domain: str) -> HomepageContext:
    crawl = page_crawl_settings()
    root = registrable_domain(domain)
    if not root:
        return HomepageContext(url="", metadata={}, markdown="")

    return fetch_site_homepage_context(root, crawl=crawl)
