"""微观利基画像：结构化字段与竞品检索 query 规划。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile

MAX_KEYWORDS = 5
MAX_MONITORING_TOPICS = 5

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

    raw_features = data.get("features")
    if isinstance(raw_features, list):
        features = [str(x).strip() for x in raw_features if str(x).strip()][:3]
    else:
        features = _split_tags(str(raw_features or ""))[:3]

    raw_customers = data.get("customers")
    if isinstance(raw_customers, list):
        customer_text = "、".join(str(x).strip() for x in raw_customers if str(x).strip())[:400]
    else:
        customer_text = str(raw_customers or "").strip()[:400]

    raw_micro = data.get("keywords")
    if isinstance(raw_micro, list):
        micro = [str(x).strip() for x in raw_micro if str(x).strip()][:MAX_KEYWORDS]
    else:
        micro = _split_tags(str(raw_micro or ""))[:MAX_KEYWORDS]

    return NicheProfile(
        company=str(data.get("company") or entity).strip()[:200],
        industry=industry,
        features="、".join(features),
        customers=customer_text,
        keywords="、".join(micro),
    )


def keywords_list(profile: NicheProfile) -> list[str]:
    return _split_tags(profile.get("keywords", ""))


def monitoring_topics_from_llm(data: dict[str, Any]) -> list[str]:
    """解析 LLM 返回的 monitoring_topics，原样采用（仅去空、截断至上限）。"""
    raw = data.get("monitoring_topics")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()][:MAX_MONITORING_TOPICS]
    return _split_tags(str(raw or ""))[:MAX_MONITORING_TOPICS]


def profile_to_dict(profile: NicheProfile) -> dict[str, str]:
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "features": profile.get("features", ""),
        "customers": profile.get("customers", ""),
        "keywords": profile.get("keywords", ""),
    }


def profile_topic_dict(profile: NicheProfile) -> dict[str, str]:
    """监测主题 LLM 用的 niche_profile 子集（含 keywords，不含 features）。"""
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "customers": profile.get("customers", ""),
        "keywords": profile.get("keywords", ""),
    }


def profile_from_dict(data: dict[str, Any]) -> NicheProfile:
    return NicheProfile(
        company=str(data.get("company") or "").strip()[:200],
        industry=str(data.get("industry") or "未知行业").strip()[:200],
        features=str(data.get("features") or "").strip()[:500],
        customers=str(data.get("customers") or "").strip()[:400],
        keywords=str(data.get("keywords") or "").strip()[:600],
    )


def merge_profile_updates(
    base: NicheProfile,
    *,
    profile_patch: dict[str, Any] | None = None,
    keywords: list[str] | None = None,
) -> NicheProfile:
    merged = profile_from_dict({**profile_to_dict(base), **(profile_patch or {})})
    if keywords is not None:
        kws = [k.strip() for k in keywords if k.strip()][:MAX_KEYWORDS]
        merged = NicheProfile(
            company=merged.get("company", ""),
            industry=merged.get("industry", ""),
            features=merged.get("features", ""),
            customers=merged.get("customers", ""),
            keywords="、".join(kws),
        )
    return merged


def build_search_query(profile: NicheProfile) -> str | None:
    """从画像字段拼一条通用检索词（供测试/工具使用）。"""
    micro = _split_tags(profile.get("keywords", ""))
    if len(micro) >= 2:
        return " ".join(micro)

    parts: list[str] = []
    industry = profile.get("industry", "")
    if industry and industry != "未知行业":
        parts.append(industry)
    parts.extend(_split_tags(profile.get("features", ""))[:3])
    parts.extend(_split_tags(profile.get("customers", ""))[:2])
    return " ".join(parts).strip() or None
