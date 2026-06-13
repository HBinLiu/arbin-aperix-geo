"""SearXNG 搜索 → 主域名候选池（按需追加 query）。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.defaults import RESULT_MIN, SEARCH_PAGE_SIZE
from aperix_geo.utils.domains import is_valid_hostname, registrable_domain
from aperix_geo.services.competitor.diagnostics import log_pool_domains, log_searxng_hit_decisions
from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.profile import build_competitor_search_queries
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.utils.url import host_resolves
from aperix_geo.utils.url import hostname_from_url
from aperix_geo.services.searxng import SearchHit, search_text

logger = logging.getLogger(__name__)


def empty_search_pool() -> SearchPool:
    return SearchPool(domains=[], hits=[], hit_by_domain={})


def planned_search_queries(profile: NicheProfile) -> list[str]:
    settings = get_settings()
    return build_competitor_search_queries(profile, max_queries=settings.competitor_search_rounds)


def _merge_hits_into_pool(
    pool: SearchPool,
    hits: list[SearchHit],
    *,
    self_domain: str,
) -> tuple[int, int, int]:
    """合并 SearXNG 结果：全部 URL 进 hits 供正文抽品牌；仅非预排除域进 domains 做交叉验算。"""
    added = 0
    skipped_domains = 0
    hits_added = 0
    seen_urls = {(h.url or "").strip() for h in pool.hits if (h.url or "").strip()}

    for hit in hits:
        host = hostname_from_url(hit.url)
        if not host:
            continue
        host = registrable_domain(host)
        if not is_valid_hostname(host) or host == self_domain:
            continue

        url = (hit.url or "").strip()
        if url and url not in seen_urls:
            pool.hits.append(hit)
            seen_urls.add(url)
            hits_added += 1

        if should_skip_domain(host):
            skipped_domains += 1
            continue

        if host not in pool.hit_by_domain:
            pool.hit_by_domain[host] = hit
            if host_resolves(host):
                pool.domains.append(host)
                added += 1
    return added, skipped_domains, hits_added


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
    added, skipped_domains, hits_added = _merge_hits_into_pool(pool, hits, self_domain=self_domain)

    new_hosts = [d for d in pool.domains if d not in before]
    log_searxng_hit_decisions(
        hits,
        self_domain=self_domain,
        pool_before=before,
        added_hosts=new_hosts,
    )
    if new_hosts:
        log_pool_domains(pool, tag="本轮新增候选", domains=new_hosts)

    if len(pool.domains) > cap:
        newer = [d for d in pool.domains if d not in before]
        older = [d for d in pool.domains if d in before]
        pool.domains = (newer + older)[:cap]

    logger.info(
        "竞品发现: 本轮 SearXNG 收录 %d 条链接、新增 %d 个交叉验算域名（池内域名 %d，来源域预排除 %d）",
        hits_added,
        added,
        len(pool.domains),
        skipped_domains,
    )
    return pool


def pool_from_web_research_rows(
    rows: list[dict[str, str]],
    *,
    exclude_domain: str | None,
) -> SearchPool:
    """将 Step1 品牌调研命中并入竞品候选池，减少 Step2 SearXNG 轮次。"""
    hits = [
        SearchHit(
            title=str(row.get("title") or ""),
            url=str(row.get("url") or ""),
            snippet=str(row.get("snippet") or ""),
            query="setup:brand_research",
        )
        for row in rows
        if isinstance(row, dict) and str(row.get("url") or "").strip()
    ]
    if not hits:
        return empty_search_pool()

    pool = empty_search_pool()
    self_domain = registrable_domain(exclude_domain) if exclude_domain else ""
    added, _skipped, _hits = _merge_hits_into_pool(pool, hits, self_domain=self_domain)
    if added:
        logger.info("竞品发现: 复用 Step1 品牌调研 %d 个主域名", added)
    return pool


def search_candidate_domains(
    profile: NicheProfile,
    *,
    exclude_domain: str | None,
    initial_pool: SearchPool | None = None,
) -> SearchPool:
    """品牌模式：按预算多轮 SearXNG，合并候选池。"""
    if not get_settings().searxng_base_url.strip():
        logger.warning("竞品发现: 未配置 SEARXNG_BASE_URL")
        return initial_pool or empty_search_pool()

    queries = planned_search_queries(profile)
    if not queries:
        return initial_pool or empty_search_pool()

    pool = initial_pool if initial_pool is not None else empty_search_pool()
    if len(pool.domains) >= RESULT_MIN:
        logger.info(
            "竞品发现: Step1 品牌调研已凑够 %d 个候选域名（目标 %d），跳过 SearXNG",
            len(pool.domains),
            RESULT_MIN,
        )
        return pool

    for round_idx, query in enumerate(queries, start=1):
        pool = run_search_query(
            profile,
            query,
            exclude_domain=exclude_domain,
            pool=pool,
            round_idx=round_idx,
            round_total=len(queries),
        )
        if len(pool.domains) >= RESULT_MIN:
            logger.info(
                "竞品发现: 品牌模式候选池已达 %d（目标 %d），停止后续搜索（第 %d/%d 轮）",
                len(pool.domains),
                RESULT_MIN,
                round_idx,
                len(queries),
            )
            break
    return pool
