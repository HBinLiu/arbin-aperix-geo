"""竞品发现编排：SearXNG 搜索 + 交叉验算（Setup Step1 画像见 setup.llm.stages.build_subject_profile）。"""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.cross_validate import (
    QUALITY_STOP_AVG_OFFSET,
    build_pack_order,
    competitor_quality_met,
    run_cross_validate,
)
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
from aperix_geo.services.competitor.types import CrossValidateResult, DiscoveredCompetitor, NicheProfile, SearchPool, SiteHead
from aperix_geo.services.providers import LLMProviderError

logger = logging.getLogger(__name__)


def _exclude_self_domain(domains: list[str], *, target: str) -> list[str]:
    self_domain = registrable_domain(target)
    return [d for d in domains if registrable_domain(d) != self_domain]


def _exclude_self_brand(brands: list[str], *, target: str) -> list[str]:
    key = target.strip().casefold()
    return [b for b in brands if b.strip().casefold() != key]


def _reachable_in_pack_order(pack_order: list[str], heads: dict[str, SiteHead]) -> int:
    return sum(1 for domain in pack_order if (head := heads.get(domain)) and head.reachable)


def _evaluate_validation(
    validation: CrossValidateResult,
    *,
    domain: str,
    min_count: int,
    package_partial: bool,
) -> tuple[list[str], bool, list[DiscoveredCompetitor]]:
    settings = get_settings()
    pack_order = build_pack_order(
        validation,
        min_score=settings.competitor_cross_validate_pass_score,
        max_keep=settings.competitor_pool_size,
    )
    pack_order = _exclude_self_domain(pack_order, target=domain)[:RESULT_MAX]
    quality_ok = competitor_quality_met(
        validation,
        pass_score=settings.competitor_cross_validate_pass_score,
        min_count=min_count,
    )
    competitors: list[DiscoveredCompetitor] = []
    if quality_ok or package_partial:
        competitors = package_discovered_competitors(
            pack_order,
            validation.heads,
            max_items=RESULT_MAX,
        )
    return pack_order, quality_ok, competitors


def _try_snippet_pool_boost(
    profile: NicheProfile,
    pool: SearchPool,
    validation: CrossValidateResult | None,
    *,
    domain: str,
    region: str,
    language: str,
) -> tuple[SearchPool, CrossValidateResult | None, list[str]]:
    from aperix_geo.services.competitor.snippet import augment_pool_from_snippet_brands

    pool, resolved = augment_pool_from_snippet_brands(
        profile,
        pool,
        domain=domain,
        region=region,
        language=language,
    )
    if not resolved or validation is None:
        return pool, validation, resolved
    validation = run_cross_validate(
        profile,
        target_domain=domain,
        pool=pool,
        prior=validation,
    )
    return pool, validation, resolved


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
    snippet_tried = False

    for round_idx, query in enumerate(queries, start=1):
        last_round = round_idx >= len(queries)
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
        pack_order, quality_ok, competitors = _evaluate_validation(
            validation,
            domain=domain,
            min_count=min_count,
            package_partial=last_round,
        )

        if quality_ok:
            stop_avg = settings.competitor_cross_validate_pass_score + QUALITY_STOP_AVG_OFFSET
            logger.info(
                "竞品发现: top%d 均分>=%.1f 且已有 %d 个可打开及格竞品，停止后续搜索（第 %d/%d 轮）",
                min_count,
                stop_avg,
                len(competitors),
                round_idx,
                len(queries),
            )
            break

        if pool.hits and not snippet_tried:
            snippet_tried = True
            pool, validation, resolved = _try_snippet_pool_boost(
                profile,
                pool,
                validation,
                domain=domain,
                region=region,
                language=language,
            )
            if resolved and validation is not None:
                pack_order, quality_ok, competitors = _evaluate_validation(
                    validation,
                    domain=domain,
                    min_count=min_count,
                    package_partial=True,
                )
                if quality_ok:
                    logger.info(
                        "竞品发现: 资讯/摘要抽取补足 %d 个及格竞品，停止后续 SearXNG（第 %d/%d 轮）",
                        len(competitors),
                        round_idx,
                        len(queries),
                    )
                    break

        if last_round:
            break

        reachable = _reachable_in_pack_order(pack_order, validation.heads)
        if reachable >= min_count:
            logger.info(
                "竞品发现: 已达 %d 个可打开竞品但质量未达标，继续搜索（第 %d/%d 轮）",
                reachable,
                round_idx,
                len(queries),
            )

        logger.info(
            "竞品发现: 当前仅 %d 个可打开竞品（目标 %d），进入第 %d/%d 轮搜索",
            reachable,
            min_count,
            round_idx + 1,
            len(queries),
        )

    if len(competitors) < min_count:
        logger.warning(
            "竞品发现: 可打开及格竞品 %d 个（目标 %d）",
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
    web_research: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    from aperix_geo.services.competitor.search import pool_from_web_research_rows

    initial_pool = (
        pool_from_web_research_rows(web_research, exclude_domain=None)
        if web_research
        else None
    )
    pool = search_candidate_domains(profile, exclude_domain=None, initial_pool=initial_pool)
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
