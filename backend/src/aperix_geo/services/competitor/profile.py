"""微观利基画像：结构化字段、检索 query、主体画像统一入口。"""

from __future__ import annotations

import logging
import re
from typing import Any

from aperix_geo.services.competitor.homepage import fetch_target_homepage
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    generate_profile_summary_via_llm,
)
from aperix_geo.services.competitor.research import (
    fetch_brand_research_hits,
    fetch_site_extra_pages,
    format_search_hits_for_llm,
    research_payload_for_domain,
)
from aperix_geo.services.competitor.types import NicheProfile

logger = logging.getLogger(__name__)

MAX_MICRO_KEYWORDS = 5

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
        company=str(data.get("company") or data.get("company_name") or entity).strip()[:200],
        industry=industry,
        core_features="、".join(features),
        target_customers=customer_text,
        micro_keywords="、".join(micro),
    )


def micro_keywords_list(profile: NicheProfile) -> list[str]:
    return _split_tags(profile.get("micro_keywords", ""))


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
        company=str(data.get("company") or data.get("company_name") or "").strip()[:200],
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


def plan_micro_keyword_queries(keywords: list[str], *, max_rounds: int) -> list[str]:
    kws: list[str] = []
    seen: set[str] = set()
    for raw in keywords:
        kw = raw.strip()
        if not kw or kw in seen:
            continue
        seen.add(kw)
        kws.append(kw)
    if not kws:
        return []

    rounds = max(1, max_rounds)
    n = len(kws)
    if n <= rounds:
        return kws

    queries: list[str] = []
    idx = 0
    for i in range(rounds):
        remaining_groups = rounds - i
        remaining_kws = n - idx
        size = (remaining_kws + remaining_groups - 1) // remaining_groups
        group = kws[idx : idx + size]
        idx += size
        queries.append(" ".join(group))
    return queries


def build_search_queries(profile: NicheProfile, *, max_queries: int) -> list[str]:
    micro = _split_tags(profile.get("micro_keywords", ""))
    if not micro:
        fallback = build_search_query(profile)
        return [fallback] if fallback else []
    return plan_micro_keyword_queries(micro, max_rounds=max_queries)


def _llm_user_payload(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
) -> dict[str, Any]:
    reg = region_label(region)
    lang = language_label(language)
    if subject_type == "domain":
        homepage = fetch_target_homepage(target)
        extra_pages = fetch_site_extra_pages(target, homepage_url=homepage.url)
        return {
            "mode": "domain",
            "target": target,
            "region": reg,
            "language": lang,
            "site_data": research_payload_for_domain(
                domain=target,
                site_metadata=homepage.metadata,
                site_markdown=homepage.markdown,
                extra_pages=extra_pages,
            ),
        }
    hits = fetch_brand_research_hits(target, region=region)
    return {
        "mode": "brand",
        "target": target.strip(),
        "region": reg,
        "language": lang,
        "web_research": format_search_hits_for_llm(hits),
    }


def build_subject_profile(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
) -> tuple[NicheProfile, str]:
    """设置向导 Step1：微观利基画像 + Markdown 摘要（domain / brand 统一入口）。"""
    target = target.strip()
    user_payload = _llm_user_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
    )
    temperature = 0.1 if subject_type == "domain" else 0.2
    data, summary = generate_profile_summary_via_llm(
        entity_key=target,
        user_payload=user_payload,
        temperature=temperature,
    )
    profile = normalize_niche_profile(data, entity=target)
    if not summary:
        summary = fallback_profile_summary(
            profile,
            entity=target,
            region_label=region_label(region),
        )
    logger.info(
        "微观利基画像: type=%s target=%r industry=%r keywords=%r",
        subject_type,
        target,
        profile["industry"],
        profile["micro_keywords"],
    )
    return profile, summary
