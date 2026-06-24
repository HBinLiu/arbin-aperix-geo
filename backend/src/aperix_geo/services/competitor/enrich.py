"""竞品 brand / aliases / summary 补全（discover 交叉验算 + Setup 用户确认）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import DiscoveredCompetitor, SiteHead
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.domains import title_alias_candidates
from aperix_geo.utils.net import ensure_brand, parse_url, registrable_from

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


def alias_seed_from_site_head(
    head: SiteHead | None,
    *,
    domain: str,
    brand: str,
) -> tuple[str, ...]:
    """SEO brand_names + title 分段别名，供 merge_competitor_aliases 合并。"""
    if head is None or not head.reachable:
        return ()
    seeds: list[str] = list(title_alias_candidates(head.title, domain=domain, brand=brand))
    seeds.extend(head.brand_names)
    return tuple(seeds)


def alias_seed_from_site_metadata(
    metadata: dict[str, Any] | None,
    *,
    domain: str,
    brand: str,
) -> tuple[str, ...]:
    """research_payload.site_data 等：从 title 提取别名种子。"""
    if not metadata:
        return ()
    title = str(metadata.get("title") or "").strip()
    if not title:
        return ()
    return tuple(title_alias_candidates(title, domain=domain, brand=brand))


def enrich_entity_aliases(
    *,
    brand: str,
    domain: str,
    existing: list[str] | None = None,
    head: SiteHead | None = None,
    site_metadata: dict[str, Any] | None = None,
) -> list[str]:
    """合并用户/会话别名与首页 title、SEO brand_names（自有品牌 / 开集品牌通用）。"""
    reg = registrable_from(domain) or (domain or "").strip()
    brand_display = ensure_brand(brand, domain=reg)
    seeds: list[str] = []
    if site_metadata:
        seeds.extend(alias_seed_from_site_metadata(site_metadata, domain=reg, brand=brand_display))
    if head is not None:
        seeds.extend(alias_seed_from_site_head(head, domain=reg, brand=brand_display))
    return merge_competitor_aliases(
        brand=brand_display,
        existing=existing,
        brand_names=tuple(seeds),
    )


def enrich_open_set_brand_aliases(
    *,
    brand: str,
    domain: str,
    website_url: str = "",
    existing: list[str] | None = None,
    head: SiteHead | None = None,
) -> list[str]:
    """开集品牌：有域名时抓 head 补全 aliases。"""
    reg = registrable_from(domain)
    if not reg:
        return normalize_competitor_aliases(existing, brand=brand)
    if head is None:
        preferred = {reg: website_url.strip()} if website_url.strip() else {}
        head = fetch_site_heads([reg], preferred_urls=preferred).get(reg)
    return enrich_entity_aliases(
        brand=brand,
        domain=reg,
        existing=existing,
        head=head,
    )


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
        head = heads.get(registrable_from(domain)) if domain else None
        brand = resolve_competitor_brand(item)
        summary = resolve_competitor_summary(head)
        aliases = enrich_entity_aliases(
            brand=brand,
            domain=domain,
            existing=item.get("aliases"),
            head=head,
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
        domain = registrable_from(str(row.get("domain") or ""))
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
    user_website_url = parse_url(str(seed.get("website_url") or ""))
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
    aliases = enrich_entity_aliases(
        brand=brand,
        domain=domain,
        existing=item.get("aliases") if isinstance(item.get("aliases"), list) else None,
        head=head,
    )
    if cache_aliases and isinstance(cache_aliases, list):
        aliases = merge_competitor_aliases(
            brand=brand,
            existing=aliases,
            seed_aliases=cache_aliases,
        )

    out = {
        "domain": domain,
        "website_url": website_url,
        "brand": brand,
        "summary": summary,
    }
    if aliases:
        out["aliases"] = aliases
    for key in ("cross_validate_score", "cross_validate_reason"):
        if key in item:
            out[key] = item[key]
    return out


def enrich_confirmed_competitors(
    competitors: list[dict[str, Any]],
    *,
    session: dict[str, Any] | None = None,
    extra_head_domains: list[str] | None = None,
    extra_preferred_urls: dict[str, str] | None = None,
    heads_out: dict[str, SiteHead] | None = None,
) -> list[dict[str, Any]]:
    """Setup 批量确认竞品补全（有 domain 时抓取 head）。"""
    if not competitors:
        return []

    cache_by_domain = _index_session_competitors_by_domain(session)
    domain_hosts: list[str] = []
    preferred_urls: dict[str, str] = dict(extra_preferred_urls or {})
    for item in competitors:
        domain = registrable_from(str(item.get("domain") or ""))
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

    for domain in extra_head_domains or []:
        reg = registrable_from(domain)
        if reg:
            domain_hosts.append(reg)

    heads = fetch_site_heads(domain_hosts, preferred_urls=preferred_urls) if domain_hosts else {}
    if heads_out is not None:
        heads_out.update(heads)

    out: list[dict[str, Any]] = []
    for item in competitors:
        domain = registrable_from(str(item.get("domain") or ""))
        head = heads.get(domain) if domain else None
        enriched = enrich_confirmed_competitor_dict(
            item,
            head=head,
            cache_seed=cache_by_domain.get(domain) if domain else None,
        )
        out.append(enriched)

    logger.info("设置向导·竞品 enrich 完成 条数=%d", len(out))
    return out
