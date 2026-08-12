"""竞品候选站首页：统一 httpx → Crawl4AI 抓取 title / meta / 结构化 SEO。"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.crawl import PageFetchResult, fetch_page, page_crawl_settings
from aperix_geo.services.crawl.metadata import PageMetadata, SeoProfile, extract_metadata_from_fetch
from aperix_geo.services.crawl.settings import PageCrawlSettings, seo_fetch_max_chars
from aperix_geo.services.crawl.seo import SeoMetadata, seo_prose_text
from aperix_geo.utils.net import explicit_http_url, homepage_fetch_urls, registrable_from

logger = logging.getLogger(__name__)

_SEO_EXCERPT_CHARS = 800


def _site_head_seo_excerpt(parsed: PageMetadata) -> str:
    supplement = SeoMetadata(
        content_type=parsed.content_type,
        brand_names=tuple(parsed.brand_names),
        schema_types=tuple(parsed.schema_types),
    )
    return seo_prose_text(supplement, max_chars=_SEO_EXCERPT_CHARS)


def _site_head_from_fetch(
    result: PageFetchResult,
    *,
    domain: str,
    html_parse_limit: int,
    seo_profile: SeoProfile,
    resolved_url: str,
) -> SiteHead:
    parsed = extract_metadata_from_fetch(
        result,
        html_parse_limit=html_parse_limit,
        include_body=False,
        seo_profile=seo_profile,
    )
    brand_names = list(parsed.brand_names)
    site_name = (parsed.site_name or "").strip()
    if site_name:
        brand_names.append(site_name)
    return SiteHead(
        domain=domain,
        title=parsed.title,
        description=parsed.description,
        reachable=True,
        seo=_site_head_seo_excerpt(parsed),
        resolved_url=resolved_url,
        brand_names=tuple(dict.fromkeys(brand_names)),
    )


def _fetch_one_sync(
    domain: str,
    *,
    crawl: PageCrawlSettings,
    seo_profile: SeoProfile,
    preferred_url: str = "",
) -> SiteHead:
    has_preferred = bool(preferred_url.strip())
    if has_preferred and not explicit_http_url(preferred_url):
        logger.debug(
            "页面抓取跳过：preferred_url 非完整 http(s) URL domain=%s url=%r",
            domain,
            preferred_url.strip(),
        )
        return SiteHead(domain=domain, title="", description="", reachable=False)

    urls = homepage_fetch_urls(
        domain,
        website_url=preferred_url,
        probe_variants=not has_preferred,
    )
    if not urls:
        return SiteHead(domain=domain, title="", description="", reachable=False)

    max_chars = seo_fetch_max_chars(crawl)
    for url in urls:
        result = fetch_page(
            url,
            crawl=crawl,
            max_chars=max_chars,
            crawl_fallback=crawl.crawl_fallback,
        )
        if not result.fetch_ok:
            continue
        resolved = (result.final_url or url).strip()
        return _site_head_from_fetch(
            result,
            domain=domain,
            html_parse_limit=max_chars,
            seo_profile=seo_profile,
            resolved_url=resolved,
        )

    logger.info("竞品 head 不可达 domain=%s", domain)
    return SiteHead(domain=domain, title="", description="", reachable=False)


async def fetch_site_heads_async(
    domains: list[str],
    *,
    concurrency: int | None = None,
    seo_profile: SeoProfile = SeoProfile.SITE_HEAD,
    preferred_urls: dict[str, str] | None = None,
) -> dict[str, SiteHead]:
    crawl = page_crawl_settings()
    conc = max(1, concurrency if concurrency is not None else crawl.concurrency)
    unique = dedupe_keys(domains)
    if not unique:
        return {}

    preferred_urls = preferred_urls or {}
    sem = asyncio.Semaphore(conc)
    out: dict[str, SiteHead] = {}

    async def run_one(host: str) -> None:
        async with sem:
            head = await asyncio.to_thread(
                _fetch_one_sync,
                host,
                crawl=crawl,
                seo_profile=seo_profile,
                preferred_url=preferred_urls.get(host, ""),
            )
            out[registrable_from(head.domain)] = head

    await asyncio.gather(*(run_one(h) for h in unique))

    return out


def fetch_site_heads(
    domains: list[str],
    *,
    concurrency: int | None = None,
    seo_profile: SeoProfile = SeoProfile.SITE_HEAD,
    preferred_urls: dict[str, str] | None = None,
) -> dict[str, SiteHead]:
    crawl = page_crawl_settings()
    unique = dedupe_keys(domains)
    if not unique:
        return {}

    preferred_urls = preferred_urls or {}
    workers = max(1, min(len(unique), concurrency if concurrency is not None else crawl.concurrency))
    out: dict[str, SiteHead] = {}

    def run_one(host: str) -> tuple[str, SiteHead]:
        head = _fetch_one_sync(
            host,
            crawl=crawl,
            seo_profile=seo_profile,
            preferred_url=preferred_urls.get(host, ""),
        )
        return registrable_from(head.domain), head

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for domain, head in pool.map(run_one, unique):
            out[domain] = head

    return out


def dedupe_keys(domains: list[str]) -> list[str]:
    return list(dict.fromkeys(registrable_from(d) for d in domains if d.strip()))
