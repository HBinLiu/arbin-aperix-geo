"""Read global page-crawl settings from application config."""

from __future__ import annotations

from dataclasses import dataclass

from aperix_geo.config import Settings, get_settings


@dataclass(frozen=True)
class PageCrawlSettings:
    fetch_timeout_s: float
    crawl_timeout_s: float
    max_chars: int
    crawl_fallback: bool
    concurrency: int
    crawl4ai_concurrency: int
    cache_ttl_s: int
    negative_cache_ttl_s: int
    dns_cache_ttl_s: int


def page_crawl_settings(settings: Settings | None = None) -> PageCrawlSettings:
    s = settings or get_settings()
    return PageCrawlSettings(
        fetch_timeout_s=s.page_crawl_fetch_timeout_s,
        crawl_timeout_s=s.page_crawl_crawl_timeout_s,
        max_chars=s.page_crawl_max_chars,
        crawl_fallback=s.page_crawl_fallback_enabled,
        concurrency=s.page_crawl_concurrency,
        crawl4ai_concurrency=s.page_crawl_crawl4ai_concurrency,
        cache_ttl_s=s.page_crawl_cache_ttl_s,
        negative_cache_ttl_s=s.page_crawl_negative_cache_ttl_s,
        dns_cache_ttl_s=s.page_crawl_dns_cache_ttl_s,
    )
