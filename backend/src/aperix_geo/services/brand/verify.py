"""Homepage verification for candidate brand primary domains."""

from __future__ import annotations

import re

from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.crawl.seo import SeoProfile
from aperix_geo.utils.net import brand_from, registrable_domain

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")


def _brand_match_key(brand: str) -> str:
    return (brand or "").strip().casefold()


def _text_mentions_brand(text: str, brand_key: str) -> bool:
    return bool(brand_key and brand_key in (text or "").casefold())


def _brand_key_has_cjk(brand_key: str) -> bool:
    return bool(_CJK_RE.search(brand_key))


def _cjk_segments(text: str) -> list[str]:
    return _CJK_RUN_RE.findall(text or "")


def _cjk_brand_mentioned_in_text(brand: str, text: str) -> bool:
    if not text:
        return False
    for segment in _cjk_segments(brand):
        if len(segment) >= 2 and segment in text:
            return True
    return False


def _domain_hosts_brand(domain: str, brand_key: str) -> bool:
    if not brand_key or not domain:
        return False
    host = domain.casefold()
    if brand_key in host:
        return True
    label = host.split(".", 1)[0]
    return brand_key == label or brand_key in label


def site_head_matches_brand(head: SiteHead, brand: str) -> bool:
    """True when homepage metadata plausibly identifies the brand."""
    if not head.reachable:
        return False

    brand_key = _brand_match_key(brand)
    if not brand_key:
        return False

    texts = [head.title, head.description, head.seo]
    for text in texts:
        if _text_mentions_brand(text, brand_key):
            return True
        if _brand_key_has_cjk(brand_key) and _cjk_brand_mentioned_in_text(brand, text):
            return True

    for name in head.brand_names:
        name_key = _brand_match_key(name)
        if name_key == brand_key or _text_mentions_brand(name, brand_key):
            return True
        if _brand_key_has_cjk(brand_key) and _cjk_brand_mentioned_in_text(brand, name):
            return True

    return False


def verify_domain_homepage(domain: str, brand: str) -> bool:
    """Fetch homepage head and check whether the site identifies as the brand."""
    normalized = brand_from(domain)
    if not normalized:
        return False
    heads = fetch_site_heads([normalized], seo_profile=SeoProfile.CROSS_VALIDATE)
    head = heads.get(normalized)
    if head is None:
        return False
    return site_head_matches_brand(head, brand)


def accept_discovered_domain(domain: str, brand: str) -> bool:
    """DNS-resolvable domain accepted when host matches brand or homepage verifies."""
    normalized = brand_from(domain)
    if not normalized or not registrable_domain(normalized):
        return False

    brand_key = _brand_match_key(brand)
    if brand_key and _domain_hosts_brand(normalized, brand_key):
        return True

    return verify_domain_homepage(normalized, brand)
