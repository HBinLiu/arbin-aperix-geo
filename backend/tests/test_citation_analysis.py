"""Tests for citation source LLM analysis normalization."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.sampling.citation import (
    ai_mentioned_brand_names,
    analyze_citation_pages_geo,
    clear_page_geo_cache,
    CitationPageMeta,
    normalize_page_geo,
    page_mentioned_brand_names,
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


def test_normalize_response_absa_filters_open_set_when_disabled() -> None:
    data = {
        "brands_sentiment_absa": {"Aperix": {"mentioned": True, "score": 75}},
        "other_brands_sentiment_absa": {"Stripe": {"mentioned": True, "score": 80}},
    }
    out = normalize_response_absa(
        data,
        own_brand="Aperix",
        competitors=["Beta"],
        open_set_enabled=False,
    )
    assert "Stripe" not in out["other_brands_sentiment_absa"]
    assert out["other_brands_sentiment_absa"] == {}


def test_normalize_page_geo_ignores_llm_brand_mentions() -> None:
    data = {
        "domain_classification": {"type": "科技/垂直行业媒体", "reason": "tech"},
        "url_classification": {"type": "实操指南", "reason": "code"},
        "page_mentioned_brands": ["Beta", "Aperix", "Stripe"],
    }
    out = normalize_page_geo(data)
    assert out["domain_classification"]["type"] == "科技/垂直行业媒体"
    assert out["page_mentioned_brands"] == []


def test_page_mentioned_brands_from_snippet() -> None:
    from aperix_geo.services.sampling.citation.page_geo import page_mentioned_brands_from_snippet

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


def _page(url: str, *, snippet: str = "Aperix review body text") -> CitationPageMeta:
    return CitationPageMeta(
        url=url,
        domain="example.com",
        http_status=200,
        title="T",
        text_snippet=snippet,
        fetch_ok=True,
    )


def test_analyze_citation_pages_geo_batch_single_call() -> None:
    clear_page_geo_cache()
    pages = [
        _page("https://example.com/a"),
        _page("https://example.com/b", snippet="generic cloud computing article"),
    ]
    calls: list[int] = []

    def _chat(messages, **kwargs):
        calls.append(len(pages))
        payload = {
            "pages": [
                {
                    "url": pages[0].url,
                    "domain_classification": {"type": "企业/品牌官网", "reason": "r1"},
                    "url_classification": {"type": "品牌官网", "reason": "r2"},
                },
                {
                    "url": pages[1].url,
                    "domain_classification": {"type": "科技/垂直行业媒体", "reason": "r3"},
                    "url_classification": {"type": "普通文章", "reason": "r4"},
                },
            ],
        }
        import json

        return json.dumps(payload), {}, 10

    with patch(
        "aperix_geo.services.sampling.citation.page_geo.chat_completion",
        side_effect=_chat,
    ):
        out = analyze_citation_pages_geo(
            pages,
            own_brand="A",
            page_brand_scope=["Aperix"],
            match_terms_by_brand={"Aperix": ["Aperix"]},
            enterprise_roots=frozenset({"example.com"}),
            cache_ttl_s=0,
            batch_size=8,
        )

    assert len(out) == 2
    assert out[0]["page_mentioned_brands"] == ["Aperix"]
    assert out[1]["page_mentioned_brands"] == []
    assert calls == [2]
