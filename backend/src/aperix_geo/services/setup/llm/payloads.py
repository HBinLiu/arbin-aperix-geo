"""Setup 向导各 LLM 阶段的 user message 构建（system 模板见 providers/prompts.py）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.homepage import fetch_target_homepage
from aperix_geo.services.competitor.profile import language_label, region_label


def _domain_site_data_payload(
    *,
    domain: str,
    site_metadata: dict[str, str],
    site_markdown: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": (site_metadata.get("title") or "").strip(),
        "description": (site_metadata.get("description") or "").strip(),
        "h1_h2": (site_metadata.get("h1_h2") or "").strip(),
    }
    seo = str(site_metadata.get("seo") or "").strip()
    if seo:
        payload["seo"] = seo[:3000]
    if site_markdown.strip():
        payload["homepage_excerpt"] = site_markdown.strip()[:6000]
    if not any(str(v).strip() for v in payload.values() if isinstance(v, str)):
        payload["domain_hint"] = domain
    return payload


def build_subject_research_payload(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
    user_corpus: str = "",
    homepage_text: str = "",
    homepage_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """discover：爬站 + 调研材料（微观利基画像 LLM）。"""
    reg = region_label(region)
    lang = language_label(language)
    if subject_type == "domain":
        metadata = dict(homepage_metadata or {})
        markdown = homepage_text.strip()
        if not metadata and not markdown:
            raw_website = (website_url or target).strip()
            data = fetch_target_homepage(target, user_url=raw_website)
            metadata = data.metadata
            markdown = (data.markdown or "").strip()
        return {
            "mode": "domain",
            "target": target,
            "region": reg,
            "language": lang,
            "site_data": _domain_site_data_payload(
                domain=target,
                site_metadata=metadata,
                site_markdown=markdown,
            ),
        }
    payload: dict[str, Any] = {
        "mode": "brand",
        "target": target.strip(),
        "region": reg,
        "language": lang,
        "user_corpus": user_corpus.strip(),
    }
    homepage = homepage_text.strip()
    url = website_url.strip()
    if homepage or url:
        payload["homepage"] = {"url": url, "text": homepage}
    return payload
