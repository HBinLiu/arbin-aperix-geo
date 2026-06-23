"""交叉验算：竞品候选站元数据 + LLM 对标打分。"""

from __future__ import annotations

import json
import logging
from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.diagnostics import log_cross_validate_score
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.utils.net import registrable_from
from aperix_geo.services.competitor.types import (
    CandidateMeta,
    CandidatePool,
    CompetitorScore,
    CrossValidateResult,
    NicheProfile,
    SiteHead,
)
from aperix_geo.services.providers.prompts import (
    COMPETITOR_CROSS_VALIDATE_SYSTEM,
    cross_validate_user_content,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def _site_fields_from_head(
    head: SiteHead | None,
    *,
    brand_fallback: str = "",
) -> dict[str, str]:
    if head is None:
        return {}
    if not head.reachable:
        return {
            "title": "（无）",
            "description": "（站点不可打开）",
        }
    title = head.title or brand_fallback[:200] or "（无）"
    description = head.description or "（无）"
    payload: dict[str, str] = {
        "title": title,
        "description": description,
    }
    if head.seo.strip():
        payload["seo"] = head.seo[:800]
    return payload


def _target_payload(
    profile: NicheProfile,
    *,
    target_domain: str,
    head: SiteHead | None = None,
) -> dict[str, str]:
    payload: dict[str, str] = {
        "domain": target_domain,
        "company": profile["company"],
        "industry": profile["industry"],
        "features": profile["features"],
        "customers": profile["customers"],
        "keywords": profile["keywords"],
    }
    payload.update(_site_fields_from_head(head, brand_fallback=profile.get("company") or ""))
    return payload


def _candidate_payload(head: SiteHead, meta: CandidateMeta | None) -> dict[str, str]:
    brand = meta.brand[:200] if meta else ""
    payload: dict[str, str] = {"domain": head.domain}
    payload.update(_site_fields_from_head(head, brand_fallback=brand))
    return payload


def _ensure_target_head(
    heads: dict[str, SiteHead],
    *,
    target_domain: str,
    target_website_url: str = "",
) -> dict[str, SiteHead]:
    key = registrable_from(target_domain)
    if not key or key in heads:
        return heads
    preferred: dict[str, str] = {}
    url = target_website_url.strip()
    if url:
        preferred[key] = url
    return {**heads, **fetch_site_heads([key], preferred_urls=preferred)}


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
        domain = registrable_from(str(row.get("domain") or ""))
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
    text, _, _latency_ms = chat_completion(messages, temperature=0.1, json_mode=True)
    try:
        data = extract_json_object(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("竞品发现: 交叉验算 JSON 解析失败", exc_info=True)
        return []

    scores = _parse_scores(data)
    return scores


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
    pool: CandidatePool,
    new_hosts: list[str],
    heads: dict[str, SiteHead],
    prior_scores: list[CompetitorScore],
) -> list[CompetitorScore]:
    target_key = registrable_from(target_domain)
    target = _target_payload(
        profile,
        target_domain=target_domain,
        head=heads.get(target_key) if target_key else None,
    )
    all_scores: list[CompetitorScore] = []
    ordered_heads = [heads[d] for d in new_hosts if d in heads]
    unreachable = [h for h in ordered_heads if not h.reachable]
    reachable_heads = [h for h in ordered_heads if h.reachable]
    if unreachable:
        all_scores.extend(
            CompetitorScore(domain=h.domain, score=0.0, reason="站点不可打开，跳过交叉验算")
            for h in unreachable
        )

    batch_size = get_settings().competitor_cross_validate_batch_size
    for i in range(0, len(reachable_heads), batch_size):
        chunk = reachable_heads[i : i + batch_size]
        payload = [_candidate_payload(h, pool.by_domain.get(h.domain)) for h in chunk]
        try:
            all_scores.extend(_score_batch(target, payload))
        except Exception:
            logger.warning("竞品发现: 交叉验算批次失败 offset=%d", i, exc_info=True)

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
    pool: CandidatePool,
    target_website_url: str = "",
    prior: CrossValidateResult | None = None,
    round_idx: int | None = None,
    round_total: int | None = None,
) -> CrossValidateResult:
    settings = get_settings()
    hosts = list(dict.fromkeys(pool.domains))[: settings.competitor_pool_size]
    if not hosts:
        return prior or CrossValidateResult(scores=[], heads={})

    prior_heads = dict(prior.heads) if prior else {}
    prior_scores = list(prior.scores) if prior else []
    heads = _ensure_target_head(
        prior_heads,
        target_domain=target_domain,
        target_website_url=target_website_url,
    )
    seen = set(heads) | {s.domain for s in prior_scores}
    new_hosts = [h for h in hosts if h not in seen]

    if not new_hosts:
        return CrossValidateResult(
            scores=_merge_score_lists(prior_scores, []),
            heads=heads,
        )

    preferred_urls = {
        d: meta.website_url
        for d in new_hosts
        if (meta := pool.by_domain.get(d)) and meta.website_url
    }
    new_heads = fetch_site_heads(new_hosts, preferred_urls=preferred_urls)
    heads = {**heads, **new_heads}
    new_scores = _score_new_hosts(
        profile,
        target_domain=target_domain,
        pool=pool,
        new_hosts=new_hosts,
        heads=heads,
        prior_scores=prior_scores,
    )
    scores = _merge_score_lists(prior_scores, new_scores)

    new_scored = {s.domain for s in new_scores}
    heads_map = heads
    for s in scores:
        if s.domain not in new_scored:
            continue
        head = heads_map.get(s.domain)
        log_cross_validate_score(
            domain=s.domain,
            score=s.score,
            reason=s.reason,
            meta=pool.by_domain.get(s.domain),
            reachable=head.reachable if head else None,
            round_idx=round_idx,
            round_total=round_total,
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
    return domains[:max_keep]
