"""微观利基画像：结构化字段与竞品检索 query 规划。"""

from __future__ import annotations

import logging
import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile

logger = logging.getLogger(__name__)

MAX_MICRO_KEYWORDS = 5
MAX_MONITORING_TOPICS = 5
_DEFAULT_MONITORING_TOPICS = (
    "品类认知与选型",
    "核心能力与方案匹配",
    "竞品对比与替代",
    "价格与采购决策",
    "口碑与风险顾虑",
)

REGION_LABELS = {"CN": "中国大陆", "HK": "中国香港", "TW": "中国台湾"}
LANGUAGE_LABELS = {
    "zh-CN": "简体中文",
    "zh-HK": "繁体中文（香港）",
    "zh-TW": "繁体中文（台湾）",
}


def region_label(region: str) -> str:
    return REGION_LABELS.get(region, region)


def language_label(language: str) -> str:
    return LANGUAGE_LABELS.get(language, language)


def _split_tags(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [p.strip() for p in re.split(r"[、,，;；\n|/]", raw) if p.strip()]


def normalize_niche_profile(data: dict[str, Any], *, entity: str) -> NicheProfile:
    industry = str(data.get("industry") or "未知行业").strip()[:200]

    raw_features = data.get("core_features")
    if isinstance(raw_features, list):
        features = [str(x).strip() for x in raw_features if str(x).strip()][:3]
    else:
        features = _split_tags(str(raw_features or ""))[:3]

    raw_customers = data.get("target_customers")
    if isinstance(raw_customers, list):
        customer_text = "、".join(str(x).strip() for x in raw_customers if str(x).strip())[:400]
    else:
        customer_text = str(raw_customers or "").strip()[:400]

    raw_micro = data.get("micro_keywords")
    if isinstance(raw_micro, list):
        micro = [str(x).strip() for x in raw_micro if str(x).strip()][:MAX_MICRO_KEYWORDS]
    else:
        micro = _split_tags(str(raw_micro or ""))[:MAX_MICRO_KEYWORDS]

    return NicheProfile(
        company=str(data.get("company") or entity).strip()[:200],
        industry=industry,
        core_features="、".join(features),
        target_customers=customer_text,
        micro_keywords="、".join(micro),
    )


def micro_keywords_list(profile: NicheProfile) -> list[str]:
    return _split_tags(profile.get("micro_keywords", ""))


def _truncate_label(text: str, *, max_len: int = 24) -> str:
    s = text.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def fallback_monitoring_topics(profile: NicheProfile) -> list[str]:
    """LLM 未返回 monitoring_topics 时，按赛道信息生成通用监测专题（非竞品检索词）。"""
    industry = (profile.get("industry") or "").strip()
    if not industry or industry == "未知行业":
        return list(_DEFAULT_MONITORING_TOPICS)

    features = _split_tags(profile.get("core_features", ""))
    customers = (profile.get("target_customers") or "").strip()

    candidates: list[str] = [
        f"{_truncate_label(industry, max_len=18)}选型与认知",
        f"{_truncate_label(features[0])}与方案能力" if features else f"{_truncate_label(industry, max_len=16)}核心能力",
        f"{_truncate_label(industry, max_len=16)}竞品对比",
        f"{_truncate_label(customers)}适用性" if customers else "价格与采购决策",
        "口碑评价与风险顾虑",
    ]

    micro = {k.lower() for k in micro_keywords_list(profile)}
    seen: set[str] = set()
    out: list[str] = []
    for topic in candidates:
        key = topic.lower()
        if key in seen or key in micro:
            continue
        seen.add(key)
        out.append(topic)
        if len(out) >= MAX_MONITORING_TOPICS:
            break
    return out or list(_DEFAULT_MONITORING_TOPICS)


def _filter_topics_against_micro(topics: list[str], profile: NicheProfile) -> list[str]:
    micro_norm = {m.lower() for m in micro_keywords_list(profile)}
    if not micro_norm:
        return topics
    return [t for t in topics if t.strip() and t.strip().lower() not in micro_norm]


def monitoring_topics_from_llm(data: dict[str, Any], profile: NicheProfile) -> list[str]:
    raw = data.get("monitoring_topics")
    if isinstance(raw, list):
        topics = [str(x).strip() for x in raw if str(x).strip()][:MAX_MONITORING_TOPICS]
    else:
        topics = _split_tags(str(raw or ""))[:MAX_MONITORING_TOPICS]
    topics = _filter_topics_against_micro(topics, profile)
    if topics:
        return topics
    return fallback_monitoring_topics(profile)


def profile_to_dict(profile: NicheProfile) -> dict[str, str]:
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "core_features": profile.get("core_features", ""),
        "target_customers": profile.get("target_customers", ""),
        "micro_keywords": profile.get("micro_keywords", ""),
    }


def profile_from_dict(data: dict[str, Any]) -> NicheProfile:
    return NicheProfile(
        company=str(data.get("company") or "").strip()[:200],
        industry=str(data.get("industry") or "未知行业").strip()[:200],
        core_features=str(data.get("core_features") or "").strip()[:500],
        target_customers=str(data.get("target_customers") or "").strip()[:400],
        micro_keywords=str(data.get("micro_keywords") or "").strip()[:600],
    )


def merge_profile_updates(
    base: NicheProfile,
    *,
    profile_patch: dict[str, Any] | None = None,
    micro_keywords: list[str] | None = None,
) -> NicheProfile:
    merged = profile_from_dict({**profile_to_dict(base), **(profile_patch or {})})
    if micro_keywords is not None:
        kws = [k.strip() for k in micro_keywords if k.strip()][:MAX_MICRO_KEYWORDS]
        merged = NicheProfile(
            company=merged.get("company", ""),
            industry=merged.get("industry", ""),
            core_features=merged.get("core_features", ""),
            target_customers=merged.get("target_customers", ""),
            micro_keywords="、".join(kws),
        )
    return merged


def build_search_query(profile: NicheProfile) -> str | None:
    micro = _split_tags(profile.get("micro_keywords", ""))
    if len(micro) >= 2:
        return " ".join(micro)

    parts: list[str] = []
    industry = profile.get("industry", "")
    if industry and industry != "未知行业":
        parts.append(industry)
    parts.extend(_split_tags(profile.get("core_features", ""))[:3])
    parts.extend(_split_tags(profile.get("target_customers", ""))[:2])
    return " ".join(parts).strip() or None


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in queries:
        q = raw.strip()
        if not q or q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


def build_competitor_search_queries(profile: NicheProfile, *, max_queries: int) -> list[str]:
    """在固定轮次预算内分配 SearXNG query：micro_keywords 优先，再行业/公司锚点。"""
    cap = max(1, max_queries)
    queries: list[str] = list(micro_keywords_list(profile))

    industry = profile.get("industry", "")
    company = profile.get("company", "")
    if industry and industry != "未知行业":
        queries.append(f"{industry} 品牌 对比")
    if company:
        queries.append(f"{company} 类似产品")

    if not queries:
        fallback = build_search_query(profile)
        if fallback:
            queries.append(fallback)

    return _dedupe_queries(queries)[:cap]
