"""Tests for citation source brand mention helpers."""

from __future__ import annotations

from aperix_geo.services.sampling.citation import (
    CitationPageMeta,
    page_mentioned_brand_names,
    page_mentioned_brands_from_snippet,
)
from aperix_geo.services.sampling.response_absa import normalize_response_absa


def test_normalize_response_absa_fills_brand_keys() -> None:
    data = {
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 75, "evidence": "推荐 Aperix"},
        },
    }
    out = normalize_response_absa(data, own_brand="Aperix", competitors=["Beta"])
    assert out["brands_sentiment_absa"]["Aperix"]["mentioned"] is True
    assert out["brands_sentiment_absa"]["Beta"]["mentioned"] is False


def test_normalize_response_absa_filters_configured_from_other() -> None:
    data = {
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 75},
            "Beta": {"mentioned": False},
        },
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 80},
            "Aperix": {"mentioned": True, "score": 95},
        },
    }
    out = normalize_response_absa(data, own_brand="Aperix", competitors=["Beta"])
    assert "Stripe" in out["other_brands_sentiment_absa"]
    assert "Aperix" not in out["other_brands_sentiment_absa"]


def test_normalize_response_absa_filters_own_alias_from_other() -> None:
    from aperix_geo.services.brand.keys import configured_brand_keys

    data = {
        "brands_sentiment_absa": {"Aperix": {"mentioned": True, "score": 75}},
        "other_brands_sentiment_absa": {
            "艾佩克斯": {"mentioned": True, "score": 95},
            "Stripe": {"mentioned": True, "score": 80},
        },
    }
    excluded = configured_brand_keys(
        own_brand="Aperix",
        own_match_names=["Aperix", "艾佩克斯", "aperix.com"],
    )
    out = normalize_response_absa(
        data,
        own_brand="Aperix",
        competitors=[],
        excluded_keys=excluded,
    )
    assert "Stripe" in out["other_brands_sentiment_absa"]
    assert "艾佩克斯" not in out["other_brands_sentiment_absa"]


def test_page_mentioned_brands_from_snippet() -> None:
    page = CitationPageMeta(
        url="https://example.com/a",
        domain="example.com",
        http_status=200,
        text_snippet="This article compares Aperix and Beta for GEO.",
        fetch_ok=True,
    )
    brands = page_mentioned_brands_from_snippet(
        page,
        page_brand_scope=["Aperix", "Beta"],
        match_terms_by_brand={"Aperix": ["Aperix"], "Beta": ["Beta"]},
    )
    assert brands == ["Aperix", "Beta"]


def test_page_mentioned_brand_names() -> None:
    page = {"page_mentioned_brands": ["Beta"]}
    assert page_mentioned_brand_names(page) == ["Beta"]
