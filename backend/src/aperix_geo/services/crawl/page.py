"""Unified page fetch: httpx first, Crawl4AI fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

import httpx

from aperix_geo.services.crawl._cache import (
    get_cached_page,
    logical_key_digest,
    set_cached_page,
    set_negative_cached_page,
)
from aperix_geo.services.crawl._crawl4ai import fetch_url_crawl4ai
from aperix_geo.services.crawl._httpx import get_httpx_client
from aperix_geo.services.crawl.limits import CrawlRateLimitError, page_crawl_slot
from aperix_geo.services.crawl.settings import PageCrawlSettings, page_crawl_settings
from aperix_geo.services.crawl.types import FetchSource, PageFetchResult
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight
from aperix_geo.utils.text import truncate_text
from aperix_geo.utils.url import (
    host_resolves,
    host_resolves_to_public_addresses,
    hostname_from_url,
    is_llm_numeric_fake_url,
    is_valid_citation_host,
    normalize_crawl_cache_url,
)

logger = logging.getLogger(__name__)

__all__ = ["FetchSource", "PageFetchResult", "fetch_page"]


@dataclass(frozen=True)
class _PageCache:
    cache_url: str
    max_chars: int
    crawl: PageCrawlSettings

    @classmethod
    def for_url(cls, request_url: str, *, crawl: PageCrawlSettings, max_chars: int) -> _PageCache:
        return cls(
            cache_url=normalize_crawl_cache_url(request_url),
            max_chars=max_chars,
            crawl=crawl,
        )

    @property
    def enabled(self) -> bool:
        return self.crawl.cache_ttl_s > 0 or self.crawl.negative_cache_ttl_s > 0

    def read(self, request_url: str) -> PageFetchResult | None:
        if not self.enabled:
            return None
        hit = get_cached_page(
            self.cache_url,
            max_chars=self.max_chars,
            crawl_fallback=self.crawl.crawl_fallback,
            ttl_s=self.crawl.cache_ttl_s,
            negative_ttl_s=self.crawl.negative_cache_ttl_s,
        )
        if hit is None:
            return None
        if hit.url == request_url:
            return hit
        return PageFetchResult(
            url=request_url,
            final_url=hit.final_url,
            http_status=hit.http_status,
            html=hit.html,
            markdown=hit.markdown,
            source=hit.source,
        )

    def store_ok(self, result: PageFetchResult) -> None:
        set_cached_page(
            self.cache_url,
            result,
            max_chars=self.max_chars,
            crawl_fallback=self.crawl.crawl_fallback,
            ttl_s=self.crawl.cache_ttl_s,
        )

    def store_negative(self, *, negative_ttl_s: int | None = None) -> None:
        ttl = self.crawl.negative_cache_ttl_s if negative_ttl_s is None else negative_ttl_s
        if ttl <= 0:
            return
        set_negative_cached_page(
            self.cache_url,
            max_chars=self.max_chars,
            crawl_fallback=self.crawl.crawl_fallback,
            negative_ttl_s=ttl,
        )


def _httpx_fetch(url: str, *, timeout_s: float, max_chars: int) -> PageFetchResult:
    key = url.strip()
    if not key:
        return PageFetchResult(url=key)

    try:
        resp = get_httpx_client().get(key, timeout=timeout_s)
        final_url = str(resp.url)
        status = resp.status_code
        if status != 200:
            return PageFetchResult(
                url=key,
                final_url=final_url,
                http_status=status,
                source="none",
            )
        html = resp.text[:max_chars]
        result = PageFetchResult(
            url=key,
            final_url=final_url,
            http_status=status,
            html=html,
            source="httpx",
        )
        if result.fetch_ok:
            return result
        return PageFetchResult(
            url=key,
            final_url=final_url,
            http_status=status,
            html=html,
            source="none",
        )
    except httpx.HTTPError:
        return PageFetchResult(url=key)


def fetch_page(
    url: str,
    *,
    crawl: PageCrawlSettings | None = None,
    max_chars: int | None = None,
    crawl_fallback: bool | None = None,
) -> PageFetchResult:
    """Fetch a page via httpx; optionally fall back to Crawl4AI when content is insufficient."""
    key = url.strip()
    if not key:
        return PageFetchResult(url=key)
    if is_llm_numeric_fake_url(key):
        logger.debug("页面抓取跳过无效引用 URL %s", key)
        return PageFetchResult(url=key)

    base_settings = crawl or page_crawl_settings()
    settings = (
        replace(base_settings, crawl_fallback=crawl_fallback)
        if crawl_fallback is not None
        else base_settings
    )
    limit = max_chars if max_chars is not None else settings.max_chars
    cache = _PageCache.for_url(key, crawl=settings, max_chars=limit)

    def _read_cache() -> PageFetchResult | None:
        return cache.read(key)

    cached = _read_cache()
    if cached is not None:
        logger.debug("页面抓取缓存命中 %s", key)
        return cached

    host = hostname_from_url(key)
    if host and not is_valid_citation_host(host):
        logger.debug("页面抓取跳过无效 host %s", key)
        if settings.negative_cache_ttl_s > 0:
            cache.store_negative()
        return PageFetchResult(url=key)
    if host and not host_resolves(host, timeout_s=2.0):
        logger.debug("页面抓取 DNS 不可解析 %s", key)
        if settings.negative_cache_ttl_s > 0:
            cache.store_negative()
        return PageFetchResult(url=key)
    if host and not host_resolves_to_public_addresses(host, timeout_s=2.0):
        logger.debug("页面抓取跳过非公开地址 %s", key)
        if settings.negative_cache_ttl_s > 0:
            cache.store_negative()
        return PageFetchResult(url=key)

    def _fetch_uncached() -> PageFetchResult:
        crawl_host = host or key
        try:
            with page_crawl_slot(crawl_host):
                return _fetch_uncached_inner()
        except CrawlRateLimitError:
            soft_ttl = settings.rate_limit_negative_ttl_s
            logger.warning(
                "页面抓取域名限流跳过 %s soft_negative_ttl_s=%d",
                crawl_host,
                soft_ttl,
            )
            if soft_ttl > 0:
                cache.store_negative(negative_ttl_s=soft_ttl)
            return PageFetchResult(url=key, final_url=key, source="none")

    def _fetch_uncached_inner() -> PageFetchResult:
        result = _httpx_fetch(key, timeout_s=settings.fetch_timeout_s, max_chars=limit)
        if result.fetch_ok or not settings.crawl_fallback:
            if result.fetch_ok:
                logger.debug("页面抓取 httpx 成功 %s", key)
                cache.store_ok(result)
            elif settings.negative_cache_ttl_s > 0:
                cache.store_negative()
            return result

        logger.info("页面抓取 httpx 未获有效内容，兜底 Crawl4AI %s", key)
        final_url, html, markdown, source = fetch_url_crawl4ai(
            result.final_url or key,
            timeout_s=settings.crawl_timeout_s,
            max_chars=limit,
            max_concurrent=settings.crawl4ai_concurrency,
        )
        if source == "none":
            failed = PageFetchResult(
                url=key,
                final_url=result.final_url or key,
                http_status=result.http_status,
                html=truncate_text(result.html, limit),
                source="none",
            )
            cache.store_negative()
            return failed

        out = PageFetchResult(
            url=key,
            final_url=final_url or result.final_url or key,
            http_status=200,
            html=html,
            markdown=markdown,
            source="crawl4ai",
        )
        cache.store_ok(out)
        return out

    if not cache.enabled:
        return _fetch_uncached()

    digest = logical_key_digest(
        cache.cache_url,
        max_chars=limit,
        crawl_fallback=settings.crawl_fallback,
    )
    wait_s = settings.fetch_timeout_s + settings.crawl_timeout_s + 15.0
    try:
        return run_single_flight(
            digest,
            wait_s=wait_s,
            read_cache=_read_cache,
            fetch=_fetch_uncached,
            lock_prefix="aperix:page_crawl:lock:",
        )
    except SingleFlightWaitTimeout:
        logger.info("页面抓取 single-flight 超时，直接抓取 %s", key)
        return _fetch_uncached()
