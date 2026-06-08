"""竞品发现编排：SearXNG 搜索 + 交叉验算（画像生成见 profile.build_subject_profile）。"""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.cross_validate import build_pack_order, run_cross_validate
from aperix_geo.services.competitor.defaults import RESULT_MAX, RESULT_MIN
from aperix_geo.services.competitor.enrich import enrich_discovered_competitors
from aperix_geo.services.competitor.profile import language_label, region_label
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.output import package_discovered_competitors
from aperix_geo.services.competitor.search import (
    empty_search_pool,
    planned_search_queries,
    run_search_query,
    search_candidate_domains,
)
from aperix_geo.services.competitor.selection import select_brand_names
from aperix_geo.services.competitor.types import CrossValidateResult, DiscoveredCompetitor, NicheProfile, SearchPool
from aperix_geo.services.providers import LLMProviderError

logger = logging.getLogger(__name__)


def _exclude_self_domain(domains: list[str], *, target: str) -> list[str]:
    self_domain = registrable_domain(target)
    return [d for d in domains if registrable_domain(d) != self_domain]


def _exclude_self_brand(brands: list[str], *, target: str) -> list[str]:
    key = target.strip().casefold()
    return [b for b in brands if b.strip().casefold() != key]


def search_domain_competitors(
    profile: NicheProfile,
    domain: str,
    *,
    region: str = "CN",
    language: str = "zh-CN",
) -> dict[str, Any]:
    """SearXNG + 交叉验算（须已有确认的微观利基画像）。"""
    settings = get_settings()
    t0 = time.perf_counter()
    min_count = RESULT_MIN

    queries = planned_search_queries(profile)
    if not queries:
        raise LLMProviderError("Cannot build SearXNG queries from niche profile")

    pool: SearchPool = empty_search_pool()
    validation: CrossValidateResult | None = None
    competitors: list[DiscoveredCompetitor] = []

    for round_idx, query in enumerate(queries, start=1):
        pool = run_search_query(
            profile,
            query,
            exclude_domain=domain,
            pool=pool,
            round_idx=round_idx,
            round_total=len(queries),
        )
        validation = run_cross_validate(
            profile,
            target_domain=domain,
            pool=pool,
            prior=validation,
        )
        pack_order = build_pack_order(
            validation,
            min_score=settings.competitor_min_score,
            max_keep=settings.competitor_pool_size,
        )
        pack_order = _exclude_self_domain(pack_order, target=domain)[:RESULT_MAX]
        competitors = package_discovered_competitors(
            pack_order,
            validation.heads,
            max_items=RESULT_MAX,
        )

        if len(competitors) >= min_count:
            logger.info(
                "竞品发现: 已达 %d 个可打开竞品，停止后续搜索（第 %d/%d 轮）",
                len(competitors),
                round_idx,
                len(queries),
            )
            break

        if round_idx < len(queries):
            logger.info(
                "竞品发现: 当前仅 %d 个可打开竞品（目标 %d），进入第 %d/%d 轮搜索",
                len(competitors),
                min_count,
                round_idx + 1,
                len(queries),
            )

    if len(competitors) < min_count:
        logger.warning(
            "竞品发现: 已用尽 %d 轮搜索，可打开及格竞品 %d 个（目标 %d）",
            len(queries),
            len(competitors),
            min_count,
        )

    heads = validation.heads if validation else {}
    competitors = enrich_discovered_competitors(
        competitors,
        profile=profile,
        subject_type="domain",
        heads=heads,
        region_label=region_label(region),
        language_label=language_label(language),
    )

    result = {"competitors": competitors}
    logger.info(
        "竞品发现: 域名搜索完成 target=%s competitors=%d %.1fs",
        domain,
        len(competitors),
        time.perf_counter() - t0,
    )
    return result


def search_brand_competitors(
    profile: NicheProfile,
    brand: str,
    *,
    region: str,
    language: str,
) -> dict[str, Any]:
    pool = search_candidate_domains(profile, exclude_domain=None)
    brands = select_brand_names(profile, brand=brand, pool=pool, region=region, language=language)
    brands = _exclude_self_brand(brands, target=brand)[:RESULT_MAX]
    if not brands:
        logger.warning("竞品发现: 品牌模式未得到有效竞品品牌")

    seeds: list[DiscoveredCompetitor] = [
        DiscoveredCompetitor(domain="", website_url="", brand=b.strip(), summary="") for b in brands if b.strip()
    ]
    competitors = enrich_discovered_competitors(
        seeds,
        profile=profile,
        subject_type="brand",
        region_label=region_label(region),
        language_label=language_label(language),
    )
    return {"competitors": competitors}
