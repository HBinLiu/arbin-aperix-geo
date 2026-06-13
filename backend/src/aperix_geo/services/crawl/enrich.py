"""Enrich search/article URLs with on-page SEO metadata via unified fetch."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from aperix_geo.services.crawl.metadata import PageMetadata, SeoProfile, extract_metadata_from_fetch
from aperix_geo.services.crawl.page import fetch_page
from aperix_geo.services.crawl.settings import PageCrawlSettings, page_crawl_settings, seo_fetch_max_chars
from aperix_geo.services.searxng import SearchHit

logger = logging.getLogger(__name__)

_DEFAULT_MAX_URLS = 8


def _unique_hit_urls(hits: list[SearchHit], *, max_urls: int) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for hit in hits:
        url = (hit.url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= max_urls:
            break
    return urls


def _fetch_one_seo(
    url: str,
    *,
    crawl: PageCrawlSettings,
    include_body: bool,
) -> tuple[str, PageMetadata]:
    max_chars = seo_fetch_max_chars(crawl)
    result = fetch_page(
        url,
        crawl=crawl,
        max_chars=max_chars,
        crawl_fallback=crawl.seo_fallback,
    )
    if not result.fetch_ok:
        logger.info(
            "竞品发现:   enrich url=%s → 抓取无效 final=%s",
            url,
            result.final_url or url,
        )
        return url, PageMetadata()
    parsed = extract_metadata_from_fetch(
        result,
        html_parse_limit=max_chars,
        include_body=include_body,
        seo_profile=SeoProfile.ARTICLE_DISCOVERY,
    )
    return url, parsed


def enrich_hit_urls(
    hits: list[SearchHit],
    *,
    max_urls: int = _DEFAULT_MAX_URLS,
    include_body: bool = False,
    concurrency: int | None = None,
) -> dict[str, PageMetadata]:
    """Fetch top article URLs and extract SEO/GEO metadata for LLM enrichment."""
    urls = _unique_hit_urls(hits, max_urls=max_urls)
    if not urls:
        return {}

    crawl = page_crawl_settings()
    workers = max(1, min(len(urls), concurrency if concurrency is not None else crawl.concurrency))
    out: dict[str, PageMetadata] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for url, parsed in pool.map(
            lambda u: _fetch_one_seo(u, crawl=crawl, include_body=include_body),
            urls,
        ):
            if parsed.has_content():
                out[url] = parsed

    if out:
        logger.info("页面 SEO  enrichment: %d/%d URLs", len(out), len(urls))
    return out
