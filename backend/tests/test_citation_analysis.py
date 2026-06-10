"""Tests for citation source LLM analysis normalization."""

from aperix_geo.services.sampling.citation import (
    ai_mentioned_brand_names,
    normalize_page_geo,
    normalize_response_absa,
    page_mentioned_brand_names,
)


def test_normalize_response_absa_fills_brand_keys() -> None:
    data = {
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 0.5, "framing_tags": ["稳定"], "evidence": "推荐 Aperix"},
        },
    }
    out = normalize_response_absa(data, own_brand="Aperix", competitors=["Beta"])
    assert out["brands_sentiment_absa"]["Aperix"]["mentioned"] is True
    assert out["brands_sentiment_absa"]["Beta"]["mentioned"] is False


def test_normalize_page_geo_page_mentioned_brands() -> None:
    data = {
        "domain_classification": {"type": "科技/垂直行业媒体", "reason": "tech"},
        "url_classification": {"type": "实操指南", "reason": "code"},
        "page_mentioned_brands": ["Beta", "Aperix"],
    }
    out = normalize_page_geo(data)
    assert out["domain_classification"]["type"] == "科技/垂直行业媒体"
    assert out["page_mentioned_brands"] == ["Beta", "Aperix"]


def test_page_and_ai_mentioned_brand_names() -> None:
    page = {"page_mentioned_brands": ["Beta"]}
    assert page_mentioned_brand_names(page) == ["Beta"]

    response = {
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True},
            "Beta": {"mentioned": False},
        }
    }
    assert ai_mentioned_brand_names(response) == ["Aperix"]
