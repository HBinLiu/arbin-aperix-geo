"""Setup 向导各 LLM 阶段的 user message 构建（system 模板见 providers/prompts.py）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.profile import (
    language_label,
    profile_to_dict,
    profile_topic_dict,
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
    """Step1 爬站 + 调研材料（微观利基画像 LLM）。"""
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
    subject_type: str,
    target: str,
    profile: NicheProfile,
) -> dict[str, Any]:
    """监测主题 LLM：主体标识与画像子集（company / industry / customers / keywords）。"""
    return {
        "subject_type": subject_type.strip(),
        "target": target.strip(),
        "niche_profile": profile_topic_dict(profile),
    }


def build_profile_summary_payload(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    profile: NicheProfile,
    competitors: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """UI Step 1→2 主体摘要 LLM：结构化画像 + 确认竞品（不含 raw crawl）。"""
    return {
        "subject_type": subject_type.strip(),
        "target": target.strip(),
        "region": region_label(region),
        "language": language_label(language),
        "niche_profile": profile_to_dict(profile),
        "competitors": [
            {
                "domain": str(item.get("domain") or "").strip(),
                "brand": str(item.get("brand") or item.get("site_name") or "").strip(),
            }
            for item in (competitors or [])
            if str(item.get("brand") or item.get("domain") or "").strip()
        ],
    }

