"""Setup 向导各 LLM 阶段的 user message 构建（system 模板见 providers/prompts.py）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.profile import (
    language_label,
    micro_keywords_list,
    profile_to_dict,
    region_label,
)
from aperix_geo.services.competitor.homepage import fetch_target_homepage
from aperix_geo.services.competitor.research import (
    fetch_brand_research_hits,
    format_search_hits_for_llm,
    research_payload_for_domain,
)
from aperix_geo.services.competitor.types import NicheProfile


def build_subject_research_payload(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
) -> dict[str, Any]:
    """Step1 爬站 + 调研材料（画像 LLM 与监测主题 LLM 共用）。"""
    reg = region_label(region)
    lang = language_label(language)
    if subject_type == "domain":
        raw_website = (website_url or target).strip()
        homepage = fetch_target_homepage(target, user_url=raw_website)
        return {
            "mode": "domain",
            "target": target,
            "region": reg,
            "language": lang,
            "site_data": research_payload_for_domain(
                domain=target,
                site_metadata=homepage.metadata,
                site_markdown=homepage.markdown,
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


def build_monitoring_topics_payload(
    *,
    research_payload: dict[str, Any],
    profile: NicheProfile,
) -> dict[str, Any]:
    """Step1b 监测主题 LLM：结构化画像 + 精简站点上下文（不含 full crawl）。"""
    payload: dict[str, Any] = {
        "subject_type": research_payload.get("mode"),
        "target": research_payload.get("target"),
        "region": research_payload.get("region"),
        "language": research_payload.get("language"),
        "niche_profile": profile_to_dict(profile),
        "micro_keywords_for_exclusion": micro_keywords_list(profile),
    }
    if research_payload.get("mode") == "domain":
        site_data = research_payload.get("site_data") or {}
        site_context: dict[str, str] = {}
        for key in ("title", "description", "h1_h2", "seo"):
            value = str(site_data.get(key) or "").strip()
            if value:
                site_context[key] = value[:500]
        excerpt = str(site_data.get("homepage_excerpt") or "").strip()
        if excerpt:
            site_context["homepage_excerpt"] = excerpt[:800]
        if site_context:
            payload["site_context"] = site_context
    else:
        rows = research_payload.get("web_research") or []
        if isinstance(rows, list) and rows:
            payload["web_research"] = rows[:3]
    return payload


def build_profile_summary_payload(
    *,
    research_payload: dict[str, Any],
    profile: NicheProfile,
    competitors: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Step2 主体摘要 LLM：结构化画像 + 竞品 enrich 结果（不再附带 raw crawl）。"""
    return {
        "subject_type": research_payload.get("mode"),
        "target": research_payload.get("target"),
        "region": research_payload.get("region"),
        "language": research_payload.get("language"),
        "niche_profile": profile_to_dict(profile),
        "competitors": [
            {
                "domain": str(item.get("domain") or "").strip(),
                "brand": str(item.get("brand") or item.get("site_name") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
            }
            for item in (competitors or [])
            if str(item.get("brand") or item.get("domain") or "").strip()
        ],
    }


def build_competitor_enrich_payload(
    *,
    profile: NicheProfile,
    subject_type: str,
    seeds: list[dict[str, Any]],
    region_label_text: str,
    language_label_text: str,
) -> dict[str, Any]:
    """Step2 竞品 brand/summary enrich LLM。"""
    return {
        "subject_type": subject_type,
        "profile": profile_to_dict(profile),
        "competitors": seeds,
        "region": region_label_text,
        "language": language_label_text,
    }
