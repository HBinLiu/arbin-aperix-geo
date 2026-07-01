"""竞品发现：域名模式（豆包 → 交叉验算）；品牌模式（豆包 URL 优先 → SearXNG 兜底）。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.brand_domain import reconcile_brand_competitor_domains
from aperix_geo.services.competitor.cross_validate import expand_ranked_domains, run_cross_validate
from aperix_geo.services.competitor.doubao import (
    discover_competitors_via_doubao,
    pool_from_discovered_competitors,
)
from aperix_geo.services.competitor.enrich import enrich_discovered_competitors
from aperix_geo.services.competitor.types import (
    CrossValidateResult,
    DiscoveredCompetitor,
    NicheProfile,
    SiteHead,
    SubjectType,
)
from aperix_geo.utils.net import registrable_from

logger = logging.getLogger(__name__)


def _exclude_self_domain(domains: list[str], *, target: str) -> list[str]:
    self_domain = registrable_from(target)
    return [d for d in domains if registrable_from(d) != self_domain]


def _merge_candidates(
    existing: dict[str, DiscoveredCompetitor],
    batch: list[DiscoveredCompetitor],
    *,
    key_fn: Callable[[DiscoveredCompetitor], str],
) -> int:
    added = 0
    for item in batch:
        key = key_fn(item)
        if not key or key in existing:
            continue
        existing[key] = item
        added += 1
    return added


def _domain_key(item: DiscoveredCompetitor) -> str:
    return registrable_from(str(item.get("domain") or ""))


def _brand_key(item: DiscoveredCompetitor) -> str:
    return str(item.get("brand") or "").strip().casefold()


def _merge_doubao_batch(
    profile: NicheProfile,
    *,
    round_idx: int,
    max_rounds: int,
    subject_type: SubjectType,
    target: str,
    website_url: str,
    region: str,
    language: str,
    key_fn: Callable[[DiscoveredCompetitor], str],
    candidates: dict[str, DiscoveredCompetitor],
    no_new_label: str,
) -> tuple[list[DiscoveredCompetitor], int]:
    """拉取一轮豆包结果并合并到 candidates；返回 (batch, added)。"""
    batch = discover_competitors_via_doubao(
        profile,
        subject_type=subject_type,
        target=target,
        website_url=website_url,
        region=region,
        language=language,
    )
    if not batch:
        return [], 0
    added = _merge_candidates(candidates, batch, key_fn=key_fn)
    if added == 0:
        logger.info("竞品发现: 第 %d/%d 轮无新%s，停止", round_idx, max_rounds, no_new_label)
    return batch, added


def _gather_doubao_candidates(
    profile: NicheProfile,
    *,
    subject_type: SubjectType,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
    key_fn: Callable[[DiscoveredCompetitor], str],
    no_new_label: str,
    early_stop_count: int | None = None,
) -> dict[str, DiscoveredCompetitor]:
    """多轮豆包联网，按 key_fn 去重合并；early_stop_count 满足时提前结束（品牌模式）。"""
    settings = get_settings()
    max_rounds = settings.competitor_search_rounds
    candidates: dict[str, DiscoveredCompetitor] = {}

    for round_idx in range(1, max_rounds + 1):
        batch, added = _merge_doubao_batch(
            profile,
            round_idx=round_idx,
            max_rounds=max_rounds,
            subject_type=subject_type,
            target=target,
            website_url=website_url,
            region=region,
            language=language,
            key_fn=key_fn,
            candidates=candidates,
            no_new_label=no_new_label,
        )
        if not batch:
            if candidates:
                break
            continue
        if added == 0:
            break
        if early_stop_count is not None and len(candidates) >= early_stop_count:
            break

    return candidates


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
        registrable_from(str(c.get("domain") or "")): c
        for c in candidates
        if c.get("domain")
    }
    out: list[DiscoveredCompetitor] = []
    for domain in pack_order:
        key = registrable_from(domain)
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
    scores_by_domain = {registrable_from(s.domain): s for s in validation.scores}
    enriched: list[DiscoveredCompetitor] = []
    for item in competitors:
        row = dict(item)
        domain = registrable_from(str(item.get("domain") or ""))
        score_row = scores_by_domain.get(domain) if domain else None
        if score_row is not None:
            row["cross_validate_score"] = score_row.score
            row["cross_validate_reason"] = score_row.reason
        enriched.append(row)  # type: ignore[arg-type]
    return enriched


def _run_domain_discover_loop(
    profile: NicheProfile,
    *,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
) -> tuple[list[DiscoveredCompetitor], CrossValidateResult | None]:
    """域名模式：豆包联网 → head 抓取 → 交叉验算 LLM 打分。"""
    settings = get_settings()
    max_rounds = settings.competitor_search_rounds
    result_min = settings.competitor_result_min
    candidate_by_key: dict[str, DiscoveredCompetitor] = {}
    validation: CrossValidateResult | None = None
    finalized: list[DiscoveredCompetitor] = []

    for round_idx in range(1, max_rounds + 1):
        batch, added = _merge_doubao_batch(
            profile,
            round_idx=round_idx,
            max_rounds=max_rounds,
            subject_type="domain",
            target=target,
            website_url=website_url,
            region=region,
            language=language,
            key_fn=_domain_key,
            candidates=candidate_by_key,
            no_new_label="域名",
        )
        if not batch:
            if finalized:
                break
            continue
        if added == 0:
            break

        pool_candidates = list(candidate_by_key.values())
        pool = pool_from_discovered_competitors(pool_candidates)
        validation = run_cross_validate(
            profile,
            target_domain=target,
            target_website_url=website_url,
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


def _run_brand_discover_loop(
    profile: NicheProfile,
    *,
    target: str,
    region: str = "CN",
    language: str = "zh-CN",
) -> tuple[list[DiscoveredCompetitor], dict[str, SiteHead]]:
    """品牌模式：豆包（brand + 可选 website_url）→ 校验 → SearXNG 兜底 → enrich。"""
    settings = get_settings()
    result_min = settings.competitor_result_min

    candidates = _gather_doubao_candidates(
        profile,
        subject_type="brand",
        target=target,
        region=region,
        language=language,
        key_fn=_brand_key,
        no_new_label="品牌",
        early_stop_count=result_min,
    )
    brand_items = list(candidates.values())[: settings.competitor_result_max]
    if not brand_items:
        return [], {}

    resolved, heads = reconcile_brand_competitor_domains(brand_items)

    if resolved and len(resolved) < result_min:
        logger.warning(
            "竞品发现: 品牌模式竞品 %d 个（目标>=%d）",
            len(resolved),
            result_min,
        )

    return resolved, heads


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
        if subject_type == "domain":
            competitors, validation = _run_domain_discover_loop(
                profile,
                target=target,
                website_url=website_url,
                region=region,
                language=language,
            )
            heads = validation.heads if validation is not None else {}
        else:
            competitors, heads = _run_brand_discover_loop(
                profile,
                target=target,
                region=region,
                language=language,
            )
            validation = None
    except Exception:
        logger.warning("竞品发现: 豆包联网失败", exc_info=True)
        return {"competitors": [], "discovery_source": "doubao"}

    if not competitors:
        return {"competitors": [], "discovery_source": "doubao"}

    competitors = enrich_discovered_competitors(competitors, heads=heads)
    if validation is not None:
        competitors = _attach_cross_validate_scores(competitors, validation)
    return {"competitors": competitors, "discovery_source": "doubao"}
