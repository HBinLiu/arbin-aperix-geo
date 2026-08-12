"""Tests for competitor brand / summary / alias helpers."""

from aperix_geo.services.competitor.enrich import (
    enrich_confirmed_competitor_dict,
    resolve_competitor_brand,
    resolve_competitor_summary,
    resolve_summary_from_site_metadata,
)
from aperix_geo.services.competitor.types import SiteHead


def test_resolve_keeps_brand_even_when_title_differs() -> None:
    item = {"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound"}
    assert resolve_competitor_brand(item) == "Profound"


def test_resolve_keeps_domainish_brand_not_title() -> None:
    item = {"domain": "wise.com", "website_url": "https://wise.com", "brand": "wise.com"}
    assert resolve_competitor_brand(item) == "wise.com"


def test_enrich_confirmed_does_not_rewrite_brand_from_title() -> None:
    head = SiteHead("wise.com", "万里汇 | 跨境支付平台", "跨境汇款", True)
    out = enrich_confirmed_competitor_dict(
        {"domain": "wise.com", "website_url": "https://wise.com", "brand": "Wise"},
        head=head,
    )
    assert out["brand"] == "Wise"
    assert out["summary"] == "跨境汇款"
    assert "万里汇" in out.get("aliases", [])


def test_resolve_summary_prefers_description_then_title() -> None:
    assert resolve_competitor_summary(SiteHead("a.com", "A Brand", "desc", True)) == "desc"
    assert resolve_competitor_summary(SiteHead("a.com", "A Brand", "", True)) == "A Brand"
    assert resolve_competitor_summary(SiteHead("a.com", "", "", False)) == ""


def test_resolve_summary_from_site_metadata() -> None:
    assert resolve_summary_from_site_metadata({"description": "全球跨境支付", "title": "Airwallex"}) == "全球跨境支付"
    assert resolve_summary_from_site_metadata({"description": "", "title": "Airwallex"}) == "Airwallex"
    assert resolve_summary_from_site_metadata({}) == ""
