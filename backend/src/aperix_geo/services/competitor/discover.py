"""竞品发现：豆包联网 → 交叉验算（head 抓取 + 打分）→ brand 规范化。"""

from __future__ import annotations

import logging
from typing import Any, Literal

from aperix_geo.config import get_settings
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.cross_validate import expand_ranked_domains, run_cross_validate
from aperix_geo.services.competitor.doubao import (
    discover_competitors_via_doubao,
    pool_from_discovered_competitors,
)
from aperix_geo.services.competitor.enrich import enrich_discovered_competitors
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.types import CrossValidateResult, DiscoveredCompetitor, NicheProfile

logger = logging.getLogger(__name__)

SubjectType = Literal["domain", "brand"]


def _exclude_self_domain(domains: list[str], *, target: str) -> list[str]:
    self_domain = registrable_domain(target)
    return [d for d in domains if registrable_domain(d) != self_domain]


def _merge_doubao_candidates(
    existing: dict[str, DiscoveredCompetitor],
    batch: list[DiscoveredCompetitor],
) -> int:
    added = 0
    for item in batch:
        domain = registrable_domain(str(item.get("domain") or ""))
        if domain:
            if domain in existing:
                continue
            existing[domain] = item
            added += 1
            continue
        brand_key = str(item.get("brand") or "").strip().casefold()
        if not brand_key:
            continue
        key = f"brand:{brand_key}"
        if key in existing:
            continue
        existing[key] = item
        added += 1
    return added


def _select_after_cross_validate(
    candidates: list[DiscoveredCompetitor],
    validation: CrossValidateResult,
    *,
    target: str,
) -> list[DiscoveredCompetitor]:
    settings = get_settings()
    pack_order = expand_ranked_domains(
        validation,
        min_score=settings.competitor_cross_validate_pass_score,
        max_keep=settings.competitor_pool_size,
    )
    pack_order = _exclude_self_domain(pack_order, target=target)[: settings.competitor_result_max]
    by_domain = {
        registrable_domain(str(c.get("domain") or "")): c
        for c in candidates
        if c.get("domain")
    }
    out: list[DiscoveredCompetitor] = []
    for domain in pack_order:
        key = registrable_domain(domain)
        item = by_domain.get(key)
        if not item:
            continue
        head = validation.heads.get(key)
        if head is not None and not head.reachable:
            continue
        if head is not None and head.resolved_url:
            item = {**item, "website_url": head.resolved_url}
        out.append(item)
    return out


def _attach_cross_validate_scores(
    competitors: list[DiscoveredCompetitor],
    validation: CrossValidateResult,
) -> list[DiscoveredCompetitor]:
    scores_by_domain = {registrable_domain(s.domain): s for s in validation.scores}
    enriched: list[DiscoveredCompetitor] = []
    for item in competitors:
        row = dict(item)
        domain = registrable_domain(str(item.get("domain") or ""))
        score_row = scores_by_domain.get(domain) if domain else None
        if score_row is not None:
            row["cross_validate_score"] = score_row.score
            row["cross_validate_reason"] = score_row.reason
        enriched.append(row)  # type: ignore[arg-type]
    return enriched


def _run_doubao_cross_validate_loop(
    profile: NicheProfile,
    *,
    subject_type: SubjectType,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
) -> tuple[list[DiscoveredCompetitor], CrossValidateResult | None]:
    settings = get_settings()
    max_rounds = settings.competitor_search_rounds
    result_min = settings.competitor_result_min
    candidate_by_key: dict[str, DiscoveredCompetitor] = {}
    validation: CrossValidateResult | None = None
    finalized: list[DiscoveredCompetitor] = []

    for round_idx in range(1, max_rounds + 1):
        batch = discover_competitors_via_doubao(
            profile,
            subject_type=subject_type,
            target=target,
            website_url=website_url,
            region=region,
            language=language,
            round_idx=round_idx,
            round_total=max_rounds,
        )
        if not batch:
            if finalized:
                break
            continue

        added = _merge_doubao_candidates(candidate_by_key, batch)
        if added == 0:
            logger.info("竞品发现: 第 %d/%d 轮无新域名，停止", round_idx, max_rounds)
            break

        pool_candidates = list(candidate_by_key.values())
        domain_candidates = [c for c in pool_candidates if c.get("domain")]
        if not domain_candidates:
            continue

        pool = pool_from_discovered_competitors(domain_candidates)
        validation = run_cross_validate(
            profile,
            target_domain=target,
            target_website_url=website_url if subject_type == "domain" else "",
            pool=pool,
            prior=validation,
            round_idx=round_idx,
            round_total=max_rounds,
        )
        finalized = _select_after_cross_validate(pool_candidates, validation, target=target)

        if len(finalized) >= result_min:
            break

    if finalized and len(finalized) < result_min:
        logger.warning(
            "竞品发现: 交叉验算后及格竞品 %d 个（目标>=%d）",
            len(finalized),
            result_min,
        )

    return finalized, validation


def discover_competitors(
    profile: NicheProfile,
    *,
    subject_type: SubjectType,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
) -> dict[str, Any]:
    """竞品发现统一入口（域名/品牌模式）。"""
    try:
        competitors, validation = _run_doubao_cross_validate_loop(
            profile,
            subject_type=subject_type,
            target=target,
            website_url=website_url,
            region=region,
            language=language,
        )
    except Exception:
        logger.warning("竞品发现: 豆包联网失败", exc_info=True)
        return {"competitors": [], "discovery_source": "doubao"}

    if not competitors or validation is None:
        return {"competitors": [], "discovery_source": "doubao"}

    competitors = enrich_discovered_competitors(
        competitors,
        heads=validation.heads,
    )
    competitors = _attach_cross_validate_scores(competitors, validation)
    return {"competitors": competitors, "discovery_source": "doubao"}


def discover_domain_competitors(
    profile: NicheProfile,
    domain: str,
    *,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
) -> dict[str, Any]:
    return discover_competitors(
        profile,
        subject_type="domain",
        target=domain,
        website_url=website_url,
        region=region,
        language=language,
    )


def discover_brand_competitors(
    profile: NicheProfile,
    brand: str,
    *,
    region: str,
    language: str,
) -> dict[str, Any]:
    return discover_competitors(
        profile,
        subject_type="brand",
        target=brand,
        region=region,
        language=language,
    )
