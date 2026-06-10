"""Tests for Page GEO batch analysis."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.sampling.citation import (
    analyze_citation_pages_geo,
    CitationPageMeta,
    clear_page_geo_cache,
)


def _page(url: str) -> CitationPageMeta:
    return CitationPageMeta(
        url=url,
        domain="example.com",
        http_status=200,
        title="T",
        text_snippet="body " * 20,
        fetch_ok=True,
    )


def test_analyze_citation_pages_geo_batch_single_call() -> None:
    clear_page_geo_cache()
    pages = [_page("https://example.com/a"), _page("https://example.com/b")]
    calls: list[int] = []

    def _chat(messages, **kwargs):
        calls.append(len(pages))
        payload = {
            "pages": [
                {
                    "url": pages[0].url,
                    "domain_classification": {"type": "企业/品牌官网", "reason": "r1"},
                    "url_classification": {"type": "品牌官网", "reason": "r2"},
                    "page_mentioned_brands": ["A"],
                },
                {
                    "url": pages[1].url,
                    "domain_classification": {"type": "科技/垂直行业媒体", "reason": "r3"},
                    "url_classification": {"type": "行业报告与深度综述", "reason": "r4"},
                    "page_mentioned_brands": [],
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
            competitors=["B"],
            cache_ttl_s=0,
            batch_size=8,
        )

    assert len(out) == 2
    assert out[0]["page_mentioned_brands"] == ["A"]
    assert calls == [2]
