"""主体调研：品牌公开信息搜索 + 首页调研 payload 组装。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.searxng import SearchHit, search_text

logger = logging.getLogger(__name__)

_REGION_SEARCH_LABELS = {"CN": "中国", "HK": "香港", "TW": "台湾"}


def fetch_brand_research_hits(brand: str, *, region: str, max_results: int = 8) -> list[SearchHit]:
    """品牌模式：SearXNG 检索公开信息摘要。"""
    brand = brand.strip()
    if not brand:
        return []
    region_hint = _REGION_SEARCH_LABELS.get(region, region)
    query = f"{brand} {region_hint} 公司 业务 产品"
    return search_text(query, max_results=max_results)


def format_search_hits_for_llm(hits: list[SearchHit], *, max_items: int = 8) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for hit in hits[:max_items]:
        rows.append(
            {
                "title": hit.title[:300],
                "url": hit.url[:500],
                "snippet": hit.snippet[:600],
            },
        )
    return rows


def research_payload_for_domain(
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
