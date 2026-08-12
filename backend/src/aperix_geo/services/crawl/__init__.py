"""Web page crawling (httpx + Crawl4AI fallback)."""

from aperix_geo.services.crawl.page import fetch_page
from aperix_geo.services.crawl.types import PageFetchResult
from aperix_geo.services.crawl.metadata import PageMetadata, SeoProfile, extract_page_metadata
from aperix_geo.services.crawl.settings import PageCrawlSettings, page_crawl_settings

__all__ = [
    "PageFetchResult",
    "PageMetadata",
    "PageCrawlSettings",
    "SeoProfile",
    "extract_page_metadata",
    "fetch_page",
    "page_crawl_settings",
]
