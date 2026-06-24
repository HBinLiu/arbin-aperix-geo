"""Tests for competitor brand normalization (post cross-validate)."""

from aperix_geo.services.competitor.enrich import (
    enrich_discovered_competitors,
    resolve_competitor_brand,
    resolve_competitor_summary,
    resolve_summary_from_site_metadata,
)
from aperix_geo.services.competitor.types import SiteHead


def test_resolve_keeps_doubao_brand_even_when_title_differs() -> None:
    item = {"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound"}
    assert resolve_competitor_brand(item) == "Profound"


def test_resolve_keeps_domainish_doubao_brand_not_title() -> None:
    item = {"domain": "wise.com", "website_url": "https://wise.com", "brand": "wise.com"}
    assert resolve_competitor_brand(item) == "wise.com"


def test_enrich_does_not_rewrite_brand_from_title() -> None:
    competitors = [
        {"domain": "wise.com", "website_url": "https://wise.com", "brand": "Wise"},
        {"domain": "paypal.com", "website_url": "https://paypal.com", "brand": "PayPal", "aliases": ["PayPal Inc"]},
    ]
    heads = {
        "wise.com": SiteHead("wise.com", "万里汇 | 跨境支付平台", "跨境汇款", True),
        "paypal.com": SiteHead("paypal.com", "PayPal: Send Money", "在线支付", True),
    }
    out = enrich_discovered_competitors(competitors, heads=heads)
    assert out[0]["brand"] == "Wise"
    assert out[0]["summary"] == "跨境汇款"
    assert "万里汇" in out[0]["aliases"]
    assert out[1]["brand"] == "PayPal"
    assert out[1]["summary"] == "在线支付"
    assert out[1]["aliases"] == ["PayPal Inc"]


def test_resolve_summary_prefers_description_then_title() -> None:
    assert resolve_competitor_summary(SiteHead("a.com", "A Brand", "desc", True)) == "desc"
    assert resolve_competitor_summary(SiteHead("a.com", "A Brand", "", True)) == "A Brand"
    assert resolve_competitor_summary(SiteHead("a.com", "", "", False)) == ""


def test_resolve_summary_from_site_metadata() -> None:
    assert resolve_summary_from_site_metadata({"description": "全球跨境支付", "title": "Airwallex"}) == "全球跨境支付"
    assert resolve_summary_from_site_metadata({"description": "", "title": "Airwallex"}) == "Airwallex"
    assert resolve_summary_from_site_metadata({}) == ""
