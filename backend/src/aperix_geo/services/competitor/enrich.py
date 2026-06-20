"""竞品 brand / aliases / summary 补全（discover 交叉验算 + Setup 用户确认）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import DiscoveredCompetitor, SiteHead
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.domains import ensure_brand, registrable_domain
from aperix_geo.utils.url import normalize_user_website_input

logger = logging.getLogger(__name__)

_SUMMARY_MAX_LEN = 500


def normalize_competitor_aliases(raw: Any, *, brand: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    brand_key = brand.casefold()
    out: list[str] = []
    seen: set[str] = {brand_key}
    for item in raw:
        alias = str(item or "").strip()[:120]
        if not alias:
            continue
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias)
    return out


def merge_competitor_aliases(
    *,
    brand: str,
    existing: list[str] | None = None,
    seed_aliases: list[str] | None = None,
    brand_names: tuple[str, ...] = (),
) -> list[str]:
    """合并用户/豆包/SEO 别名，去重且不含 canonical brand。"""
    out = normalize_competitor_aliases(existing or [], brand=brand)
    seen = {alias.casefold() for alias in out}
    seen.add(brand.casefold())
    for source in list(seed_aliases or []) + list(brand_names):
        alias = str(source or "").strip()[:120]
        if not alias:
            continue
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias)
    return out


def _discovered_item(
    item: DiscoveredCompetitor,
    *,
    domain: str,
    brand: str,
    summary: str,
    aliases: list[str] | None = None,
) -> DiscoveredCompetitor:
    out: DiscoveredCompetitor = {
        "domain": domain,
        "website_url": str(item.get("website_url") or "").strip(),
        "brand": brand[:255],
        "summary": summary[:_SUMMARY_MAX_LEN],
    }
    if aliases:
        out["aliases"] = aliases
    return out


def resolve_competitor_brand(item: DiscoveredCompetitor) -> str:
    """保留豆包 brand，仅做 ensure_brand 规范化；head title 不参与 brand。"""
    domain = str(item.get("domain") or "").strip()
    seed = str(item.get("brand") or "").strip()
    return ensure_brand(seed, domain=domain)


def resolve_summary_from_site_metadata(metadata: dict[str, Any] | None) -> str:
    """站点 meta：优先 description，否则 title（与竞品 head 规则一致）。"""
    if not metadata:
        return ""
    description = str(metadata.get("description") or "").strip()
    if description:
        return description[:_SUMMARY_MAX_LEN]
    title = str(metadata.get("title") or "").strip()
    if title:
        return title[:_SUMMARY_MAX_LEN]
    return ""


def resolve_competitor_summary(head: SiteHead | None) -> str:
    """交叉验算抓取的 head：优先 meta description，否则用 title。"""
    if head is None or not head.reachable:
        return ""
    return resolve_summary_from_site_metadata(
        {"description": head.description, "title": head.title},
    )


def enrich_discovered_competitors(
    competitors: list[DiscoveredCompetitor],
    *,
    heads: dict[str, SiteHead] | None = None,
) -> list[DiscoveredCompetitor]:
    """discover 阶段：为豆包竞品补充 brand / summary / aliases（summary 总是来自 head）。"""
    if not competitors:
        return []

    heads = heads or {}
    out: list[DiscoveredCompetitor] = []
    for item in competitors:
        domain = str(item.get("domain") or "").strip()
        head = heads.get(registrable_domain(domain)) if domain else None
        brand = resolve_competitor_brand(item)
        summary = resolve_competitor_summary(head)
        aliases = merge_competitor_aliases(
            brand=brand,
            existing=item.get("aliases"),
            brand_names=head.brand_names if head else (),
        )
        out.append(
            _discovered_item(
                item,
                domain=domain,
                brand=brand,
                summary=summary,
                aliases=aliases or None,
            )
        )
    logger.info("竞品 enrich: %d 条", len(out))
    return out


def _index_session_competitors_by_domain(session: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not session:
        return out
    cached = session.get("competitors")
    if not isinstance(cached, list):
        return out
    for row in cached:
        if not isinstance(row, dict):
            continue
        domain = registrable_domain(str(row.get("domain") or ""))
        if domain and domain not in out:
            out[domain] = row
    return out


def _confirmed_seed_item(
    item: dict[str, Any],
    *,
    cache_seed: dict[str, Any] | None,
) -> dict[str, Any]:
    cache_seed = cache_seed or {}
    domain = str(item.get("domain") or cache_seed.get("domain") or "").strip()
    website_url = str(item.get("website_url") or cache_seed.get("website_url") or "").strip()
    brand = str(item.get("brand") or cache_seed.get("brand") or "").strip()
    seed: dict[str, Any] = {
        "domain": domain,
        "website_url": website_url,
        "brand": brand,
    }
    cache_aliases = cache_seed.get("aliases")
    if isinstance(cache_aliases, list) and cache_aliases:
        seed["aliases"] = list(cache_aliases)
    item_aliases = item.get("aliases")
    if isinstance(item_aliases, list) and item_aliases:
        seed["aliases"] = list(item_aliases)
    return seed


def enrich_confirmed_competitor_dict(
    item: dict[str, Any],
    *,
    head: SiteHead | None = None,
    cache_seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Setup 单条确认竞品：brand 规范化；summary 空才用 head；aliases 合并缓存与 SEO。"""
    domain_raw = str(item.get("domain") or "").strip()
    if not domain_raw:
        brand = ensure_brand(str(item.get("brand") or ""))
        aliases = normalize_competitor_aliases(item.get("aliases"), brand=brand)
        out: dict[str, Any] = {
            "domain": "",
            "website_url": "",
            "brand": brand,
            "summary": str(item.get("summary") or "").strip(),
        }
        if aliases:
            out["aliases"] = aliases
        return out

    seed = _confirmed_seed_item(item, cache_seed=cache_seed)
    user_website_url = normalize_user_website_input(str(seed.get("website_url") or ""))
    domain, website_url = prepare_domain_and_website_url(
        domain_raw,
        user_website_url,
        probe=not bool(user_website_url),
    )
    if not user_website_url and head is not None and head.resolved_url:
        website_url = head.resolved_url.strip()
    seed["domain"] = domain
    seed["website_url"] = website_url

    brand = resolve_competitor_brand(seed)  # type: ignore[arg-type]

    summary = str(item.get("summary") or "").strip()
    if not summary:
        summary = resolve_competitor_summary(head)

    cache_aliases = cache_seed.get("aliases") if cache_seed else None
    aliases = merge_competitor_aliases(
        brand=brand,
        existing=item.get("aliases") if isinstance(item.get("aliases"), list) else None,
        seed_aliases=cache_aliases if isinstance(cache_aliases, list) else None,
        brand_names=head.brand_names if head else (),
    )

    out = {
        "domain": domain,
        "website_url": website_url,
        "brand": brand,
        "summary": summary,
    }
    if aliases:
        out["aliases"] = aliases
    return out


def enrich_confirmed_competitors(
    competitors: list[dict[str, Any]],
    *,
    session: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Setup 批量确认竞品补全（有 domain 时抓取 head）。"""
    if not competitors:
        return []

    cache_by_domain = _index_session_competitors_by_domain(session)
    domain_hosts: list[str] = []
    preferred_urls: dict[str, str] = {}
    for item in competitors:
        domain = registrable_domain(str(item.get("domain") or ""))
        if not domain:
            continue
        domain_hosts.append(domain)
        url = str(item.get("website_url") or "").strip()
        if url:
            preferred_urls[domain] = url
        elif cache := cache_by_domain.get(domain):
            cached_url = str(cache.get("website_url") or "").strip()
            if cached_url:
                preferred_urls[domain] = cached_url

    heads = fetch_site_heads(domain_hosts, preferred_urls=preferred_urls) if domain_hosts else {}

    out: list[dict[str, Any]] = []
    for item in competitors:
        domain = registrable_domain(str(item.get("domain") or ""))
        head = heads.get(domain) if domain else None
        enriched = enrich_confirmed_competitor_dict(
            item,
            head=head,
            cache_seed=cache_by_domain.get(domain) if domain else None,
        )
        out.append(enriched)

    logger.info("设置向导·竞品 enrich 完成 条数=%d", len(out))
    return out
