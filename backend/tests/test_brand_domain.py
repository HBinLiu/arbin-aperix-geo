"""Tests for brand domain resolution helpers."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.brand.domain import (
    _pick_brand_domain_from_search_hits,
    extract_domain_from_text_for_brand,
    other_entity_id,
    search_brand_official_domain,
)
from aperix_geo.services.searxng import SearchHit


def test_other_entity_id_stable() -> None:
    assert other_entity_id("Stripe") == other_entity_id("stripe")
    assert other_entity_id("Stripe").startswith("other:")


def test_extract_domain_from_nearby_url() -> None:
    text = "推荐 Stripe（https://stripe.com/payments）用于跨境收款。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", ["https://stripe.com/payments"])
    assert domain == "stripe.com"


def test_extract_domain_from_host_match() -> None:
    text = "也可以访问 stripe.com 了解详情。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", [])
    assert domain == "stripe.com"


def _hit(title: str, url: str, *, snippet: str = "") -> SearchHit:
    return SearchHit(title=title, url=url, snippet=snippet, query="q")


def test_pick_search_domain_prefers_host_match_over_earlier_hit() -> None:
    hits = [
        _hit("Stripe news", "https://techcrunch.com/stripe-funding"),
        _hit("Stripe | Payments", "https://stripe.com/pricing"),
    ]
    assert _pick_brand_domain_from_search_hits("Stripe", hits) == "stripe.com"


def test_pick_search_domain_skips_unmatched_domains() -> None:
    hits = [
        _hit("Payments roundup", "https://techcrunch.com/payments"),
        _hit("Wiki", "https://en.wikipedia.org/wiki/Stripe"),
    ]
    assert _pick_brand_domain_from_search_hits("Stripe", hits) == ""


def test_pick_search_domain_falls_back_to_title_match() -> None:
    hits = [
        _hit("贝宝中国", "https://www.paypal.com/cn/"),
    ]
    assert _pick_brand_domain_from_search_hits("贝宝", hits) == "paypal.com"


def test_pick_search_domain_ignores_snippet_only_match() -> None:
    hits = [
        _hit("Weekly fintech digest", "https://techcrunch.com/fintech", snippet="Stripe raised funding"),
    ]
    assert _pick_brand_domain_from_search_hits("Stripe", hits) == ""


@patch("aperix_geo.services.brand.domain.search_text")
@patch("aperix_geo.services.brand.domain.get_settings")
def test_search_brand_official_domain_requires_brand_match(mock_settings, mock_search) -> None:
    mock_settings.return_value.searxng_base_url = "http://searxng"
    mock_search.return_value = [
        _hit("Roundup", "https://techcrunch.com/stripe"),
        _hit("Stripe", "https://stripe.com/"),
    ]

    assert search_brand_official_domain("Stripe") == "stripe.com"
    mock_search.assert_called_once()
