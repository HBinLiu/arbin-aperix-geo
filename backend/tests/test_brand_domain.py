"""Tests for brand domain resolution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.brand.domain import (
    _pick_brand_from_search_hits,
    _search_queries_for_brand,
    domain_plausibly_matches_brand,
    extract_domain_from_text_for_brand,
    other_entity_id,
    search_brand_official_domain,
)
from aperix_geo.services.searxng import SearchHit


def test_other_entity_id_stable() -> None:
    assert other_entity_id("Stripe") == other_entity_id("stripe")
    assert other_entity_id("Stripe").startswith("other:")


def test_search_queries_are_chinese_only() -> None:
    queries = _search_queries_for_brand("光引GEO")
    assert queries == [
        "光引GEO 官网",
        "光引GEO 官方网站",
        "光引GEO 官网地址",
    ]
    assert not any("official" in q.casefold() for q in queries)


def test_domain_plausibly_matches_brand() -> None:
    assert domain_plausibly_matches_brand("stripe.com", "Stripe")
    assert not domain_plausibly_matches_brand("zgswcn.com", "透镜GEO")


def test_extract_domain_from_nearby_url() -> None:
    text = "推荐 Stripe（https://stripe.com/payments）用于跨境收款。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", ["https://stripe.com/payments"])
    assert domain == "stripe.com"


def test_extract_domain_from_host_match() -> None:
    text = "也可以访问 stripe.com 了解详情。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", [])
    assert domain == "stripe.com"


def test_extract_domain_prefers_citation_url_over_text_score() -> None:
    text = "DeepRank 的情感得分是 96.8，详情见 https://deeprank.ai/about。"
    domain = extract_domain_from_text_for_brand(text, "DeepRank", ["https://deeprank.ai/about"])
    assert domain == "deeprank.ai"


def test_extract_domain_ignores_absa_score_near_brand() -> None:
    text = "DeepRank 的情感得分是 96.8，整体表现不错。"
    domain = extract_domain_from_text_for_brand(text, "DeepRank", [])
    assert domain == ""


def test_extract_domain_ignores_decimal_without_letters() -> None:
    text = "ImpetaAI（99.5）在 GEO 领域表现突出。"
    domain = extract_domain_from_text_for_brand(text, "ImpetaAI", [])
    assert domain == ""


def _hit(title: str, url: str, *, snippet: str = "") -> SearchHit:
    return SearchHit(title=title, url=url, snippet=snippet, query="q")


@patch("aperix_geo.services.brand.domain._verified_domain")
def test_pick_search_domain_prefers_host_match_over_earlier_hit(mock_verified: MagicMock) -> None:
    mock_verified.side_effect = lambda domain, brand: domain if domain == "stripe.com" else ""
    hits = [
        _hit("Stripe news", "https://techcrunch.com/stripe-funding"),
        _hit("Stripe | Payments", "https://stripe.com/pricing"),
    ]
    assert _pick_brand_from_search_hits("Stripe", hits) == "stripe.com"


@patch("aperix_geo.services.brand.domain._verified_domain", return_value="")
def test_pick_search_domain_skips_unmatched_domains(_mock_verified: MagicMock) -> None:
    hits = [
        _hit("Payments roundup", "https://techcrunch.com/payments"),
        _hit("Wiki", "https://en.wikipedia.org/wiki/Stripe"),
    ]
    assert _pick_brand_from_search_hits("Stripe", hits) == ""


@patch("aperix_geo.services.brand.domain._verified_domain")
def test_pick_search_domain_falls_back_to_title_match(mock_verified: MagicMock) -> None:
    mock_verified.side_effect = lambda domain, brand: domain if domain == "paypal.com" else ""
    hits = [
        _hit("贝宝中国", "https://www.paypal.com/cn/"),
    ]
    assert _pick_brand_from_search_hits("贝宝", hits) == "paypal.com"


@patch("aperix_geo.services.brand.domain._verified_domain", return_value="")
def test_pick_search_domain_skips_media_title_for_latin_brand(_mock_verified: MagicMock) -> None:
    hits = [
        _hit("DeepRank GEO 深度评测", "https://www.sohu.com/a/974974141"),
    ]
    assert _pick_brand_from_search_hits("DeepRank", hits) == ""


@patch("aperix_geo.services.brand.domain._verified_domain", return_value="")
def test_pick_search_domain_ignores_snippet_only_match(_mock_verified: MagicMock) -> None:
    hits = [
        _hit("Weekly fintech digest", "https://techcrunch.com/fintech", snippet="Stripe raised funding"),
    ]
    assert _pick_brand_from_search_hits("Stripe", hits) == ""


@patch("aperix_geo.services.brand.domain._verified_domain")
@patch("aperix_geo.services.brand.domain.search_text")
@patch("aperix_geo.services.brand.domain.get_settings")
def test_search_brand_official_domain_requires_brand_match(
    mock_settings: MagicMock,
    mock_search: MagicMock,
    mock_verified: MagicMock,
) -> None:
    mock_settings.return_value.searxng_base_url = "http://searxng"
    mock_search.return_value = [
        _hit("Roundup", "https://techcrunch.com/stripe"),
        _hit("Stripe", "https://stripe.com/"),
    ]
    mock_verified.side_effect = lambda domain, brand: domain if domain == "stripe.com" else ""

    assert search_brand_official_domain("Stripe") == "stripe.com"
    assert mock_search.call_count == 3
