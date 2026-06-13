"""Tests for site research helpers."""

from unittest.mock import patch

from aperix_geo.services.competitor.research import (
    format_search_hits_for_llm,
    research_payload_for_domain,
)
from aperix_geo.services.searxng import SearchHit


def test_research_payload_from_homepage_only() -> None:
    payload = research_payload_for_domain(
        domain="example.com",
        site_metadata={
            "title": "示例",
            "description": "描述",
            "h1_h2": "产品 | 解决方案",
            "seo": "keywords: GEO, SaaS",
        },
        site_markdown="首页正文",
    )
    assert payload["title"] == "示例"
    assert payload["homepage_excerpt"] == "首页正文"
    assert payload["seo"] == "keywords: GEO, SaaS"
    assert "extra_pages" not in payload


def test_format_search_hits_for_llm() -> None:
    hits = [
        SearchHit(title="A 公司", url="https://a.com", snippet="snippet" * 20, query="q"),
    ]
    rows = format_search_hits_for_llm(hits)
    assert rows[0]["title"] == "A 公司"
    assert len(rows[0]["snippet"]) <= 600


@patch("aperix_geo.services.competitor.research.search_text")
def test_fetch_brand_research_hits(mock_search) -> None:
    from aperix_geo.services.competitor.research import fetch_brand_research_hits

    mock_search.return_value = [
        SearchHit(title="T", url="https://t.com", snippet="s", query="q"),
    ]
    hits = fetch_brand_research_hits("深睿医疗", region="CN")
    assert len(hits) == 1
    mock_search.assert_called_once()
    assert "深睿医疗" in mock_search.call_args[0][0]
