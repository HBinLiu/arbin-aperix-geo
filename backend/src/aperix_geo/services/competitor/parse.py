"""豆包竞品 JSON 解析。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.enrich import normalize_competitor_aliases
from aperix_geo.services.competitor.types import DiscoveredCompetitor, SubjectType
from aperix_geo.utils.json import extract_json_object
from aperix_geo.utils.net import ensure_brand, explicit_http_url, registrable_from


def _brand_only_item(row: dict[str, Any], *, brand: str) -> DiscoveredCompetitor:
    aliases = normalize_competitor_aliases(row.get("aliases"), brand=brand)
    item: DiscoveredCompetitor = {"domain": "", "website_url": "", "brand": brand}
    if aliases:
        item["aliases"] = aliases
    return item


def _url_from_row(row: dict[str, Any]) -> str:
    return str(row.get("website_url") or row.get("url") or "").strip()


def _apply_parsed_url(item: DiscoveredCompetitor, raw_url: str) -> bool:
    validated = explicit_http_url(raw_url)
    if not validated:
        return False
    domain = registrable_from(validated)
    if not domain:
        return False
    item["domain"] = domain
    item["website_url"] = validated
    return True


def _parse_competitor_row(
    row: dict[str, Any],
    *,
    mode: SubjectType,
    self_domain: str,
    self_brand: str,
) -> DiscoveredCompetitor | None:
    brand = str(row.get("brand") or "").strip()[:255]
    if not brand:
        return None
    if self_brand and brand.casefold() == self_brand.casefold():
        return None

    aliases = normalize_competitor_aliases(row.get("aliases"), brand=brand)
    raw_url = _url_from_row(row)

    if mode == "brand":
        item = _brand_only_item(row, brand=brand)
        if raw_url:
            _apply_parsed_url(item, raw_url)
        return item

    if not raw_url:
        return None

    item: DiscoveredCompetitor = {"domain": "", "website_url": "", "brand": brand}
    if not _apply_parsed_url(item, raw_url):
        return None
    if item["domain"] == self_domain:
        return None

    item["brand"] = ensure_brand(brand, domain=item["domain"])[:255]
    if aliases:
        item["aliases"] = aliases
    return item


def parse_doubao_competitors_payload(
    text: str,
    *,
    mode: SubjectType,
    self_domain: str = "",
    self_brand: str = "",
) -> list[DiscoveredCompetitor]:
    """解析豆包 Responses 返回的 competitors JSON。"""
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
            mode=mode,
            self_domain=self_domain,
            self_brand=self_brand,
        )
        if item is None:
            continue
        domain = item["domain"]
        brand_key = item["brand"].casefold()
        if mode == "brand":
            if brand_key in seen_brands:
                continue
            seen_brands.add(brand_key)
        elif domain:
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
        else:
            if brand_key in seen_brands:
                continue
            seen_brands.add(brand_key)
        out.append(item)
    return out
