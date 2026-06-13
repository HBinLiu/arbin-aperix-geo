"""交叉验算：竞品候选站元数据 + LLM 对标打分。"""

from __future__ import annotations

import json
import logging
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.defaults import (
    CROSS_VALIDATE_BATCH_SIZE,
    RESULT_MAX,
)
from aperix_geo.services.competitor.diagnostics import log_cross_validate_score
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.services.competitor.types import (
    CompetitorScore,
    CrossValidateResult,
    NicheProfile,
    SearchPool,
    SiteHead,
)
from aperix_geo.services.providers.prompts import (
    COMPETITOR_CROSS_VALIDATE_SYSTEM,
    cross_validate_user_content,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object
from aperix_geo.services.searxng import SearchHit

logger = logging.getLogger(__name__)

# 停搜质量线 = PASS_SCORE + 该偏移（避免 3 个刚及格分就结束 SearXNG）
QUALITY_STOP_AVG_OFFSET = 0.5


def _target_payload(profile: NicheProfile, *, target_domain: str) -> dict[str, str]:
    return {
        "domain": target_domain,
        "company": profile["company"],
        "industry": profile["industry"],
        "core_features": profile["core_features"],
        "target_customers": profile["target_customers"],
        "micro_keywords": profile["micro_keywords"],
    }


def _candidate_payload(head: SiteHead, hit: SearchHit | None) -> dict[str, str]:
    title = head.title or (hit.title[:200] if hit else "")
    description = head.description or (hit.snippet[:400] if hit else "")
    payload = {
        "domain": head.domain,
        "title": title or "（无）",
        "description": description or "（无）",
    }
    if head.seo.strip():
        payload["seo"] = head.seo[:800]
    return payload


def _parse_scores(data: dict[str, Any]) -> list[CompetitorScore]:
    rows = data.get("scores")
    if not isinstance(rows, list):
        if data.get("domain") is not None and "score" in data:
            rows = [data]
        else:
            return []

    out: list[CompetitorScore] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        domain = registrable_domain(str(row.get("domain") or ""))
        if not domain:
            continue
        try:
            score = float(row.get("score", 0))
        except (TypeError, ValueError):
            continue
        out.append(
            CompetitorScore(
                domain=domain,
                score=max(0.0, min(10.0, score)),
                reason=str(row.get("reason") or "").strip()[:300],
            ),
        )
    return out


def _score_batch(
    target: dict[str, str],
    candidates: list[dict[str, str]],
) -> list[CompetitorScore]:
    messages = [
        {"role": "system", "content": COMPETITOR_CROSS_VALIDATE_SYSTEM},
        {
            "role": "user",
            "content": cross_validate_user_content(
                target_json=json.dumps(target, ensure_ascii=False, indent=2),
                candidates_json=json.dumps(candidates, ensure_ascii=False, indent=2),
            ),
        },
    ]
    text, _, latency_ms = chat_completion(messages, temperature=0.1, json_mode=True)
    try:
        data = extract_json_object(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("竞品发现: 交叉验算 JSON 解析失败", exc_info=True)
        return []

    scores = _parse_scores(data)
    logger.info(
        "竞品发现: 交叉验算批次 %d 候选 %dms 返回 %d 条",
        len(candidates),
        latency_ms,
        len(scores),
    )
    return scores


def _count_reachable_high_scores(
    scores: list[CompetitorScore],
    heads: dict[str, SiteHead],
    *,
    min_score: float,
) -> int:
    n = 0
    for s in scores:
        if s.score < min_score:
            continue
        head = heads.get(s.domain)
        if head and head.reachable:
            n += 1
    return n


def _score_sort_key(s: CompetitorScore, heads: dict[str, SiteHead]) -> tuple[float, int, str]:
    """分数从高到低；同分时可打开的靠前（便于打包补位）。"""
    head = heads.get(s.domain)
    reachable_rank = 0 if (head and head.reachable) else 1
    return (-s.score, reachable_rank, s.domain)


def _merge_score_lists(
    prior: list[CompetitorScore],
    new: list[CompetitorScore],
) -> list[CompetitorScore]:
    best: dict[str, CompetitorScore] = {s.domain: s for s in prior}
    for s in new:
        prev = best.get(s.domain)
        if prev is None or s.score > prev.score:
            best[s.domain] = s
    return sorted(best.values(), key=lambda s: (-s.score, s.domain))


def _score_new_hosts(
    profile: NicheProfile,
    *,
    target_domain: str,
    pool: SearchPool,
    new_hosts: list[str],
    heads: dict[str, SiteHead],
    prior_scores: list[CompetitorScore],
) -> list[CompetitorScore]:
    settings = get_settings()
    target = _target_payload(profile, target_domain=target_domain)
    min_score = settings.competitor_cross_validate_pass_score
    stop_at = RESULT_MAX
    all_scores: list[CompetitorScore] = []
    ordered_heads = [heads[d] for d in new_hosts if d in heads]
    unreachable = [h for h in ordered_heads if not h.reachable]
    reachable_heads = [h for h in ordered_heads if h.reachable]
    if unreachable:
        logger.info("竞品发现: %d 个站点不可打开，跳过 LLM 交叉验算", len(unreachable))
        all_scores.extend(
            CompetitorScore(domain=h.domain, score=0.0, reason="站点不可打开，跳过交叉验算")
            for h in unreachable
        )

    for i in range(0, len(reachable_heads), CROSS_VALIDATE_BATCH_SIZE):
        chunk = reachable_heads[i : i + CROSS_VALIDATE_BATCH_SIZE]
        payload = [_candidate_payload(h, pool.hit_by_domain.get(h.domain)) for h in chunk]
        try:
            all_scores.extend(_score_batch(target, payload))
        except Exception:
            logger.warning("竞品发现: 交叉验算批次失败 offset=%d", i, exc_info=True)

        merged = _merge_score_lists(prior_scores, all_scores)
        reachable_high = _count_reachable_high_scores(merged, heads, min_score=min_score)
        if reachable_high >= stop_at:
            logger.info(
                "竞品发现: 可打开且高分候选已够 %d 个，提前结束交叉验算",
                stop_at,
            )
            break

    scored = {s.domain for s in all_scores}
    for h in reachable_heads:
        if h.domain not in scored:
            all_scores.append(
                CompetitorScore(domain=h.domain, score=0.0, reason="交叉验算未返回分数"),
            )
    return all_scores


def run_cross_validate(
    profile: NicheProfile,
    *,
    target_domain: str,
    pool: SearchPool,
    prior: CrossValidateResult | None = None,
) -> CrossValidateResult:
    settings = get_settings()
    hosts = list(dict.fromkeys(pool.domains))[: settings.competitor_pool_size]
    if not hosts:
        return prior or CrossValidateResult(scores=[], heads={})

    prior_heads = dict(prior.heads) if prior else {}
    prior_scores = list(prior.scores) if prior else []
    seen = set(prior_heads) | {s.domain for s in prior_scores}
    new_hosts = [h for h in hosts if h not in seen]

    if not new_hosts:
        return CrossValidateResult(
            scores=_merge_score_lists(prior_scores, []),
            heads=prior_heads,
        )

    new_heads = fetch_site_heads(new_hosts)
    heads = {**prior_heads, **new_heads}
    new_scores = _score_new_hosts(
        profile,
        target_domain=target_domain,
        pool=pool,
        new_hosts=new_hosts,
        heads=heads,
        prior_scores=prior_scores,
    )
    scores = _merge_score_lists(prior_scores, new_scores)

    heads_map = heads
    for s in scores:
        head = heads_map.get(s.domain)
        log_cross_validate_score(
            domain=s.domain,
            score=s.score,
            reason=s.reason,
            hit=pool.hit_by_domain.get(s.domain),
            reachable=head.reachable if head else None,
        )

    return CrossValidateResult(scores=scores, heads=heads)


def expand_ranked_domains(
    result: CrossValidateResult,
    *,
    min_score: float,
    max_keep: int,
    heads: dict[str, SiteHead] | None = None,
) -> list[str]:
    """仅包含分数 >= min_score 的域名，按得分从高到低排序（不做低分顺延）。"""
    heads = heads if heads is not None else result.heads
    passing = [s for s in result.scores if s.score >= min_score]
    passing.sort(key=lambda s: _score_sort_key(s, heads))
    domains = list(dict.fromkeys(s.domain for s in passing))
    logger.info(
        "竞品发现: 及格竞品 %d 个（>=%.1f）按分数排序 %s",
        len(domains[:max_keep]),
        min_score,
        domains[:max_keep],
    )
    return domains[:max_keep]


def build_pack_order(
    validation: CrossValidateResult,
    *,
    min_score: float,
    max_keep: int,
) -> list[str]:
    """打包顺序：及格分域名按分数降序，供 package 取前 N 个可打开站点。"""
    return expand_ranked_domains(
        validation,
        min_score=min_score,
        max_keep=max_keep,
        heads=validation.heads,
    )


def competitor_quality_met(
    validation: CrossValidateResult,
    *,
    pass_score: float,
    min_count: int,
) -> bool:
    """可打开及格竞品数量与 top-N 均分（pass_score + QUALITY_STOP_AVG_OFFSET）同时达标时可停搜。"""
    min_top_avg = pass_score + QUALITY_STOP_AVG_OFFSET
    heads = validation.heads
    passing = [s for s in validation.scores if s.score >= pass_score]
    passing.sort(key=lambda s: _score_sort_key(s, heads))
    reachable = [
        s
        for s in passing
        if (head := heads.get(s.domain)) is not None and head.reachable
    ]
    if len(reachable) < min_count:
        return False
    top = reachable[:min_count]
    avg = sum(s.score for s in top) / len(top)
    return avg >= min_top_avg
