"""品牌模式竞品：豆包 website_url 优先 → SearXNG 兜底 → 批量抓首页 enrich。"""

from __future__ import annotations

import logging

from aperix_geo.services.brand.domain import search_brand_official_domain
from aperix_geo.services.brand.verify import accept_discovered_domain
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import DiscoveredCompetitor, SiteHead
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.net import coalesce_explicit_http_url, explicit_http_url, registrable_from

logger = logging.getLogger(__name__)


def _resolve_brand_domain(
    brand: str,
    *,
    candidate_domain: str = "",
    candidate_url: str = "",
) -> str:
    """豆包候选域先过 accept_discovered_domain；失败再 SearXNG。"""
    normalized = registrable_from(candidate_domain or candidate_url)
    preferred_url = explicit_http_url(candidate_url)
    if preferred_url and registrable_from(preferred_url) != normalized:
        preferred_url = ""
    if normalized:
        if accept_discovered_domain(normalized, brand, preferred_url=preferred_url):
            logger.info("竞品发现: 豆包官网 brand=%s domain=%s", brand, normalized)
            return normalized
        logger.info("竞品发现: 豆包 URL 未通过校验 brand=%s domain=%s", brand, normalized)

    domain = search_brand_official_domain(brand)
    if domain:
        logger.info("竞品发现: SearXNG 官网 brand=%s domain=%s", brand, domain)
        return domain

    logger.info("竞品发现: 未找到官网 brand=%s", brand)
    return ""


def _row_from_domain(
    item: DiscoveredCompetitor,
    *,
    domain: str,
    heads: dict[str, SiteHead],
) -> tuple[DiscoveredCompetitor, SiteHead | None]:
    if not domain:
        row = dict(item)
        row["domain"] = ""
        row["website_url"] = ""
        return row, None  # type: ignore[return-value]

    head = heads.get(registrable_from(domain))
    doubao_url = coalesce_explicit_http_url(str(item.get("website_url") or ""))
    fetch_url = coalesce_explicit_http_url(
        head.resolved_url if head and head.reachable else "",
        doubao_url,
    )

    verified_domain, website_url = prepare_domain_and_website_url(
        domain,
        fetch_url,
        probe=False,
    )
    if not verified_domain:
        verified_domain = registrable_from(domain)

    row = dict(item)
    row["domain"] = verified_domain
    row["website_url"] = coalesce_explicit_http_url(website_url, fetch_url, doubao_url)
    return row, head  # type: ignore[return-value]


def reconcile_brand_competitor_domain(
    item: DiscoveredCompetitor,
) -> tuple[DiscoveredCompetitor, SiteHead | None]:
    """单条 reconcile（测试 / 工具）；批量路径请用 reconcile_brand_competitor_domains。"""
    resolved, heads = reconcile_brand_competitor_domains([item])
    row = resolved[0] if resolved else item
    key = registrable_from(str(row.get("domain") or ""))
    return row, heads.get(key)


def reconcile_brand_competitor_domains(
    items: list[DiscoveredCompetitor],
) -> tuple[list[DiscoveredCompetitor], dict[str, SiteHead]]:
    if not items:
        return [], {}

    resolved_domains: list[str] = []
    preferred_urls: dict[str, str] = {}
    for item in items:
        brand = str(item.get("brand") or "").strip()
        if not brand:
            resolved_domains.append("")
            continue
        candidate_domain = str(item.get("domain") or "").strip()
        candidate_url = str(item.get("website_url") or "").strip()
        resolved_domains.append(
            _resolve_brand_domain(
                brand,
                candidate_domain=candidate_domain,
                candidate_url=candidate_url,
            )
        )
        reg = registrable_from(candidate_domain or candidate_url)
        fetch_url = coalesce_explicit_http_url(candidate_url)
        if reg and fetch_url and registrable_from(fetch_url) == reg:
            preferred_urls[reg] = fetch_url

    unique_domains = sorted({registrable_from(d) for d in resolved_domains if d})
    heads = (
        fetch_site_heads(unique_domains, preferred_urls=preferred_urls)
        if unique_domains
        else {}
    )

    out: list[DiscoveredCompetitor] = []
    collected_heads: dict[str, SiteHead] = {}
    for item, domain in zip(items, resolved_domains, strict=True):
        brand = str(item.get("brand") or "").strip()
        if not brand:
            out.append(item)
            continue
        row, head = _row_from_domain(item, domain=domain, heads=heads)
        out.append(row)
        key = registrable_from(str(row.get("domain") or ""))
        if key and head is not None:
            collected_heads[key] = head

    return out, collected_heads
