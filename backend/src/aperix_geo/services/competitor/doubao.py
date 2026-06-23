"""豆包联网竞品发现。"""

from __future__ import annotations

from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.profile import language_label, region_label
from aperix_geo.services.competitor.types import CandidateMeta, CandidatePool, DiscoveredCompetitor, NicheProfile
from aperix_geo.services.providers.doubao import doubao_responses_chat
from aperix_geo.services.providers.errors import DoubaoProviderError
from aperix_geo.services.providers.prompts import (
    COMPETITOR_DOUBAO_DISCOVER_SYSTEM,
    competitor_doubao_discover_user_content,
)
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.net import ensure_brand, registrable_from
from aperix_geo.utils.json import extract_json_object


def _normalize_aliases(raw: Any, *, brand: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    brand_key = brand.casefold()
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        alias = str(item or "").strip()[:120]
        if not alias or alias.casefold() == brand_key:
            continue
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias)
    return out


def _parse_competitor_row(
    row: dict[str, Any],
    *,
    self_domain: str,
    require_domain: bool,
) -> DiscoveredCompetitor | None:
    brand = str(row.get("brand") or "").strip()[:255]
    if not brand:
        return None

    raw_domain = str(row.get("domain") or "").strip()
    raw_url = str(row.get("website_url") or row.get("url") or "").strip()
    if not raw_url:
        return None
    domain, website_url = prepare_domain_and_website_url(raw_domain, raw_url, probe=False)
    if not website_url:
        return None
    if require_domain and not domain:
        return None
    if domain and domain == self_domain:
        return None

    aliases = _normalize_aliases(row.get("aliases"), brand=brand)
    item: DiscoveredCompetitor = {
        "domain": domain,
        "website_url": website_url,
        "brand": ensure_brand(brand, domain=domain)[:255],
    }
    if aliases:
        item["aliases"] = aliases
    return item


def parse_doubao_competitors_payload(
    text: str,
    *,
    self_domain: str,
    require_domain: bool,
) -> list[DiscoveredCompetitor]:
    data = extract_json_object(text)
    rows = data.get("competitors")
    if not isinstance(rows, list):
        return []

    self_domain = registrable_from(self_domain)
    out: list[DiscoveredCompetitor] = []
    seen_domains: set[str] = set()
    seen_brands: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        item = _parse_competitor_row(
            row,
            self_domain=self_domain,
            require_domain=require_domain,
        )
        if item is None:
            continue
        domain = item["domain"]
        brand_key = item["brand"].casefold()
        if domain:
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
        else:
            if brand_key in seen_brands:
                continue
            seen_brands.add(brand_key)
        out.append(item)
    return out


def pool_from_discovered_competitors(competitors: list[DiscoveredCompetitor]) -> CandidatePool:
    """将豆包 JSON 竞品转为交叉验算候选池。"""
    domains: list[str] = []
    by_domain: dict[str, CandidateMeta] = {}
    for item in competitors:
        domain = registrable_from(str(item.get("domain") or ""))
        if not domain or domain in by_domain:
            continue
        url = str(item.get("website_url") or "").strip() or f"https://{domain}/"
        by_domain[domain] = CandidateMeta(
            domain=domain,
            brand=str(item.get("brand") or "").strip(),
            website_url=url,
        )
        domains.append(domain)
    return CandidatePool(domains=domains, by_domain=by_domain)


def discover_competitors_via_doubao(
    profile: NicheProfile,
    *,
    subject_type: str,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
    round_idx: int | None = None,
    round_total: int | None = None,
) -> list[DiscoveredCompetitor]:
    """调用豆包 Responses API（联网）抽取竞品列表。"""
    settings = get_settings()
    if not settings.doubao_api_key.strip():
        raise DoubaoProviderError("Doubao API key is not configured")

    require_domain = subject_type == "domain"
    self_domain = registrable_from(target if require_domain else "")
    user_content = competitor_doubao_discover_user_content(
        target=target,
        website_url=website_url,
        profile=profile,
        region=region_label(region),
        language=language_label(language),
    )

    result = doubao_responses_chat(
        [{"role": "user", "content": user_content}],
        api_key=settings.doubao_api_key,
        base_url=settings.doubao_base_url,
        model=settings.doubao_model,
        web_search=settings.doubao_web_search_enabled,
        timeout_s=settings.doubao_responses_timeout_s,
        system_prompt=COMPETITOR_DOUBAO_DISCOVER_SYSTEM,
    )

    competitors = parse_doubao_competitors_payload(
        result.text,
        self_domain=self_domain,
        require_domain=require_domain,
    )
    return competitors
