"""微观利基画像：结构化字段与竞品检索 query 规划。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile

MAX_SEARCH_QUERIES = 5
MAX_LEXICON_TERMS = 6

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


def _join_tags(items: list[str], *, limit: int) -> str:
    return "、".join(items[:limit])


def _normalize_term_list(raw: Any, *, limit: int) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()][:limit]
    return _split_tags(str(raw or ""))[:limit]


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

    search_queries = _join_tags(
        _normalize_term_list(data.get("search_queries"), limit=MAX_SEARCH_QUERIES),
        limit=MAX_SEARCH_QUERIES,
    )

    lexicon_raw = data.get("topic_lexicon")
    if not isinstance(lexicon_raw, dict):
        lexicon_raw = {}
    category_terms = _join_tags(
        _normalize_term_list(lexicon_raw.get("category_terms"), limit=MAX_LEXICON_TERMS),
        limit=MAX_LEXICON_TERMS,
    )
    scenario_terms = _join_tags(
        _normalize_term_list(lexicon_raw.get("scenario_terms"), limit=MAX_LEXICON_TERMS),
        limit=MAX_LEXICON_TERMS,
    )
    audience_terms = _join_tags(
        _normalize_term_list(lexicon_raw.get("audience_terms"), limit=MAX_LEXICON_TERMS),
        limit=MAX_LEXICON_TERMS,
    )
    pain_terms = _join_tags(
        _normalize_term_list(lexicon_raw.get("pain_terms"), limit=MAX_LEXICON_TERMS),
        limit=MAX_LEXICON_TERMS,
    )

    return NicheProfile(
        company=str(data.get("company") or entity).strip()[:200],
        industry=industry,
        features="、".join(features),
        customers=customer_text,
        search_queries=search_queries,
        category_terms=category_terms,
        scenario_terms=scenario_terms,
        audience_terms=audience_terms,
        pain_terms=pain_terms,
    )


def search_queries_list(profile: NicheProfile) -> list[str]:
    return _split_tags(profile.get("search_queries", ""))


def topic_lexicon_dict(profile: NicheProfile) -> dict[str, list[str]]:
    return {
        "category_terms": _split_tags(profile.get("category_terms", "")),
        "scenario_terms": _split_tags(profile.get("scenario_terms", "")),
        "audience_terms": _split_tags(profile.get("audience_terms", "")),
        "pain_terms": _split_tags(profile.get("pain_terms", "")),
    }


def profile_to_dict(profile: NicheProfile) -> dict[str, str]:
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "features": profile.get("features", ""),
        "customers": profile.get("customers", ""),
        "search_queries": profile.get("search_queries", ""),
        "category_terms": profile.get("category_terms", ""),
        "scenario_terms": profile.get("scenario_terms", ""),
        "audience_terms": profile.get("audience_terms", ""),
        "pain_terms": profile.get("pain_terms", ""),
    }


def profile_topic_dict(profile: NicheProfile) -> dict[str, Any]:
    """监测主题流水线用的 niche_profile 子集。"""
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "features": profile.get("features", ""),
        "customers": profile.get("customers", ""),
        **topic_lexicon_dict(profile),
    }


def profile_from_dict(data: dict[str, Any]) -> NicheProfile:
    search_queries = str(data.get("search_queries") or "").strip()[:600]
    return NicheProfile(
        company=str(data.get("company") or "").strip()[:200],
        industry=str(data.get("industry") or "未知行业").strip()[:200],
        features=str(data.get("features") or "").strip()[:500],
        customers=str(data.get("customers") or "").strip()[:400],
        search_queries=search_queries,
        category_terms=str(data.get("category_terms") or "").strip()[:600],
        scenario_terms=str(data.get("scenario_terms") or "").strip()[:600],
        audience_terms=str(data.get("audience_terms") or "").strip()[:600],
        pain_terms=str(data.get("pain_terms") or "").strip()[:600],
    )


def merge_profile_updates(
    base: NicheProfile,
    *,
    profile_patch: dict[str, Any] | None = None,
    search_queries: list[str] | None = None,
) -> NicheProfile:
    merged = profile_from_dict({**profile_to_dict(base), **(profile_patch or {})})
    if search_queries is not None:
        kws = [k.strip() for k in search_queries if k.strip()][:MAX_SEARCH_QUERIES]
        merged = NicheProfile(
            company=merged.get("company", ""),
            industry=merged.get("industry", ""),
            features=merged.get("features", ""),
            customers=merged.get("customers", ""),
            search_queries="、".join(kws),
            category_terms=merged.get("category_terms", ""),
            scenario_terms=merged.get("scenario_terms", ""),
            audience_terms=merged.get("audience_terms", ""),
            pain_terms=merged.get("pain_terms", ""),
        )
    return merged


def build_search_query(profile: NicheProfile) -> str | None:
    """从画像字段拼一条通用检索词（供测试/工具使用）。"""
    micro = search_queries_list(profile)
    if len(micro) >= 2:
        return " ".join(micro)

    parts: list[str] = []
    industry = profile.get("industry", "")
    if industry and industry != "未知行业":
        parts.append(industry)
    lexicon = topic_lexicon_dict(profile)
    parts.extend(lexicon.get("category_terms", [])[:3])
    parts.extend(_split_tags(profile.get("features", ""))[:3])
    parts.extend(_split_tags(profile.get("customers", ""))[:2])
    return " ".join(parts).strip() or None
