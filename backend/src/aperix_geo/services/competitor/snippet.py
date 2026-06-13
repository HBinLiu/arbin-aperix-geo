"""从 SearXNG 摘要抽取竞品品牌名并解析官网域名，扩充候选池。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.brand.domain import (
    extract_domain_from_text_for_brand,
    search_brand_official_domain,
)
from aperix_geo.services.competitor.diagnostics import log_enrich_urls
from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.selection import (
    _MAX_HITS_IN_PROMPT,
    _hit_text_for_llm,
    format_search_block,
    select_brand_names,
)
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.services.crawl.enrich import enrich_hit_urls
from aperix_geo.services.crawl.metadata import PageMetadata
from aperix_geo.services.searxng import SearchHit
from aperix_geo.utils.domains import is_valid_hostname, registrable_domain
from aperix_geo.utils.url import host_resolves

logger = logging.getLogger(__name__)


def _target_brand_label(profile: NicheProfile, *, domain: str) -> str:
    company = str(profile.get("company") or "").strip()
    if company and company not in {"未知公司", "未知"}:
        return company
    return domain.strip()


def _merge_domain_into_pool(
    pool: SearchPool,
    *,
    domain: str,
    brand: str,
    self_domain: str,
) -> bool:
    host = registrable_domain(domain)
    if not host or not is_valid_hostname(host) or host == self_domain:
        return False
    if should_skip_domain(host):
        return False
    if host in pool.hit_by_domain:
        return False
    if not host_resolves(host):
        return False
    hit = SearchHit(
        title=f"{brand} 官网",
        url=f"https://{host}/",
        snippet=f"由搜索摘要抽取竞品 {brand} 并解析官网",
        query="setup:snippet",
    )
    pool.hits.append(hit)
    pool.hit_by_domain[host] = hit
    pool.domains.append(host)
    return True


def _publisher_domains(pool: SearchPool) -> set[str]:
    return {registrable_domain(d) for d in pool.domains if d}


def resolve_brand_official_domain_from_pool(
    brand: str,
    pool: SearchPool,
    *,
    seo_by_url: dict[str, PageMetadata] | None = None,
) -> str:
    """先从摘要/正文解析域名（排除文章来源站），再 SearXNG 搜官网。"""
    publishers = _publisher_domains(pool)
    seo_map = seo_by_url or {}

    for hit in pool.hits[:_MAX_HITS_IN_PROMPT]:
        prose = _hit_text_for_llm(hit, seo_map.get((hit.url or "").strip()))
        from_hit = extract_domain_from_text_for_brand(prose, brand, None)
        domain = registrable_domain(from_hit)
        if domain and domain not in publishers:
            return domain

    search_text = format_search_block(pool, seo_by_url=seo_map)
    from_text = extract_domain_from_text_for_brand(search_text, brand, None)
    domain = registrable_domain(from_text)
    if domain and domain not in publishers:
        return domain

    resolved = search_brand_official_domain(brand)
    domain = registrable_domain(resolved)
    if domain and domain not in publishers:
        return domain
    return ""


def augment_pool_from_snippet_brands(
    profile: NicheProfile,
    pool: SearchPool,
    *,
    domain: str,
    region: str,
    language: str,
    max_brands: int | None = None,
) -> tuple[SearchPool, list[str]]:
    """从摘要抽取竞品品牌并解析官网，合并进候选池。"""
    from aperix_geo.services.competitor.defaults import RESULT_MAX, SEARCH_PAGE_SIZE

    if not pool.hits:
        return pool, []

    cap = max_brands if max_brands is not None else RESULT_MAX
    target = _target_brand_label(profile, domain=domain)
    self_domain = registrable_domain(domain)

    max_urls = min(len(pool.hits), SEARCH_PAGE_SIZE)
    seo_by_url = enrich_hit_urls(pool.hits, include_body=True, max_urls=max_urls)
    enrich_urls = list(dict.fromkeys((h.url or "").strip() for h in pool.hits if (h.url or "").strip()))[:max_urls]
    log_enrich_urls(enrich_urls, seo_by_url)

    brand_names = select_brand_names(
        profile,
        brand=target,
        pool=pool,
        region=region,
        language=language,
        seo_by_url=seo_by_url,
    )
    target_key = target.casefold()
    brand_names = [b for b in brand_names if b.strip().casefold() != target_key][:cap]

    if not brand_names:
        logger.info(
            "竞品发现: 摘要未抽到有效竞品品牌，跳过官网解析（见上方 enrich url 与 SearXNG 条目）",
        )
        return pool, []

    added: list[str] = []
    for brand in brand_names:
        resolved = resolve_brand_official_domain_from_pool(brand, pool, seo_by_url=seo_by_url)
        if not resolved:
            logger.info("竞品发现: 摘要竞品 %r 未能解析官网", brand)
            continue
        if _merge_domain_into_pool(pool, domain=resolved, brand=brand, self_domain=self_domain or ""):
            added.append(resolved)
            logger.info("竞品发现: 摘要竞品 %r → %s", brand, resolved)

    cap_pool = get_settings().competitor_pool_size
    if len(pool.domains) > cap_pool:
        pool.domains = pool.domains[-cap_pool:]

    if added:
        logger.info("竞品发现: 摘要解析新增 %d 个官网域名 %s", len(added), added)
    return pool, added
