"""SearXNG 搜索 → 主域名候选池（按需追加 query）。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.defaults import SEARCH_PAGE_SIZE
from aperix_geo.utils.domains import is_valid_hostname, registrable_domain
from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.profile import build_search_queries
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.utils.url import host_resolves
from aperix_geo.utils.url import hostname_from_url
from aperix_geo.services.searxng import SearchHit, search_text

logger = logging.getLogger(__name__)


def empty_search_pool() -> SearchPool:
    return SearchPool(domains=[], hits=[], hit_by_domain={})


def planned_search_queries(profile: NicheProfile) -> list[str]:
    settings = get_settings()
    return build_search_queries(profile, max_queries=settings.competitor_search_rounds)


def _merge_hits_into_pool(
    pool: SearchPool,
    hits: list[SearchHit],
    *,
    self_domain: str,
) -> tuple[int, int]:
    added = 0
    skipped = 0
    for hit in hits:
        host = hostname_from_url(hit.url)
        if not host:
            continue
        host = registrable_domain(host)
        if not is_valid_hostname(host) or host == self_domain:
            continue
        if should_skip_domain(host):
            skipped += 1
            continue
        pool.hits.append(hit)
        if host not in pool.hit_by_domain:
            pool.hit_by_domain[host] = hit
            if host_resolves(host):
                pool.domains.append(host)
                added += 1
    return added, skipped


def run_search_query(
    profile: NicheProfile,
    query: str,
    *,
    exclude_domain: str | None,
    pool: SearchPool | None = None,
    round_idx: int | None = None,
    round_total: int | None = None,
) -> SearchPool:
    settings = get_settings()
    if pool is None:
        pool = empty_search_pool()

    if not settings.searxng_base_url.strip():
        logger.warning("竞品发现: 未配置 SEARXNG_BASE_URL")
        return pool

    self_domain = registrable_domain(exclude_domain) if exclude_domain else ""
    cap = settings.competitor_pool_size
    before = set(pool.domains)

    if round_idx is not None and round_total is not None:
        logger.info("竞品发现: 第 %d/%d 轮 SearXNG query=%r", round_idx, round_total, query)
    else:
        logger.info("竞品发现: SearXNG query=%r", query)

    hits = search_text(query, max_results=SEARCH_PAGE_SIZE)
    added, skipped = _merge_hits_into_pool(pool, hits, self_domain=self_domain)

    if len(pool.domains) > cap:
        newer = [d for d in pool.domains if d not in before]
        older = [d for d in pool.domains if d in before]
        pool.domains = (newer + older)[:cap]

    logger.info(
        "竞品发现: 本轮 SearXNG 新增 %d 个主域名（池内共 %d，预排除 %d）",
        added,
        len(pool.domains),
        skipped,
    )
    return pool


def search_candidate_domains(
    profile: NicheProfile,
    *,
    exclude_domain: str | None,
) -> SearchPool:
    """仅执行第一条备用搜索词。"""
    if not get_settings().searxng_base_url.strip():
        logger.warning("竞品发现: 未配置 SEARXNG_BASE_URL")
        return empty_search_pool()

    queries = planned_search_queries(profile)
    if not queries:
        return empty_search_pool()

    return run_search_query(profile, queries[0], exclude_domain=exclude_domain)
