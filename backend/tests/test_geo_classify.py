"""Tests for schema + rule citation GEO classification."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.sampling.citation.geo_classify import (
    classify_citation_page_geo,
    merge_geo_analysis,
)
from aperix_geo.services.sampling.citation.page import CitationPageMeta
from aperix_geo.services.sampling.citation.page_geo import analyze_citation_pages_geo


def _page(
    url: str,
    *,
    domain: str = "",
    schema_types: list[str] | None = None,
    content_type: str = "",
    has_code_block: bool = False,
    has_table: bool = False,
    text_snippet: str = "body text",
    http_status: int = 200,
    fetch_ok: bool = True,
) -> CitationPageMeta:
    return CitationPageMeta(
        url=url,
        domain=domain or url.split("/")[2],
        http_status=http_status,
        schema_types=schema_types or [],
        content_type=content_type,
        has_code_block=has_code_block,
        has_table=has_table,
        text_snippet=text_snippet,
        fetch_ok=fetch_ok,
    )


def test_schema_maps_howto_to_guide() -> None:
    page = _page(
        "https://docs.example.com/setup",
        schema_types=["HowTo"],
        text_snippet="Step one install the package.",
    )
    cls = classify_citation_page_geo(page, enterprise_roots=frozenset())
    assert cls.url_type == "实操指南"
    assert "schema.org" in cls.url_reason


def test_github_domain_is_code_platform() -> None:
    page = _page("https://github.com/org/repo", domain="github.com")
    cls = classify_citation_page_geo(page, enterprise_roots=frozenset())
    assert cls.domain_type == "代码/开源平台"
    assert cls.domain_resolved


def test_enterprise_root_homepage_is_brand_site() -> None:
    page = _page(
        "https://aperix.com/",
        domain="aperix.com",
        content_type="website",
    )
    cls = classify_citation_page_geo(page, enterprise_roots=frozenset({"aperix.com"}))
    assert cls.url_type == "品牌官网"
    assert cls.domain_type == "企业/品牌官网"
    assert cls.complete


def test_code_block_triggers_guide_without_llm() -> None:
    page = _page(
        "https://blog.example.com/post",
        has_code_block=True,
        text_snippet="```python\nprint('hi')\n```",
    )
    cls = classify_citation_page_geo(page, enterprise_roots=frozenset())
    assert cls.url_type == "实操指南"
    assert cls.url_reason == "has_code_block"


def test_compare_review_when_table_and_multi_brand() -> None:
    snippet = "Aperix vs Beta comparison table with scores"
    page = _page(
        "https://media.example.com/compare",
        has_table=True,
        text_snippet=snippet,
    )
    cls = classify_citation_page_geo(
        page,
        enterprise_roots=frozenset(),
        page_brand_scope=["Aperix", "Beta"],
    )
    assert cls.url_type == "对比评测"


def test_merge_prefers_rule_over_llm() -> None:
    from aperix_geo.services.sampling.citation.geo_classify import GeoClassification

    rule = GeoClassification(
        url_type="实操指南",
        url_reason="has_code_block",
        domain_type="",
        domain_reason="",
    )
    llm = {
        "url_classification": {"type": "普通文章", "reason": "llm guess"},
        "domain_classification": {"type": "科技/垂直行业媒体", "reason": "media"},
        "analysis_source": "llm",
    }
    merged = merge_geo_analysis(rule, llm)
    assert merged["url_classification"]["type"] == "实操指南"
    assert merged["domain_classification"]["type"] == "科技/垂直行业媒体"
    assert merged["analysis_source"] == "hybrid"


def test_analyze_skips_llm_when_rules_complete() -> None:
    page = _page(
        "https://github.com/org/repo",
        domain="github.com",
        has_code_block=True,
        text_snippet="code sample",
    )
    with patch(
        "aperix_geo.services.sampling.citation.page_geo.chat_completion",
    ) as chat:
        out = analyze_citation_pages_geo(
            [page],
            own_brand="Aperix",
            page_brand_scope=["Aperix"],
            match_terms_by_brand={"Aperix": ["Aperix"]},
            cache_ttl_s=0,
        )
    chat.assert_not_called()
    assert out[0]["analysis_source"] == "rule"
    assert out[0]["domain_classification"]["type"] == "代码/开源平台"
    assert out[0]["url_classification"]["type"] == "实操指南"


def test_analyze_llm_fallback_only_for_unresolved() -> None:
    page = _page(
        "https://unknown.example.com/article",
        text_snippet="generic industry commentary without strong signals",
    )
    calls: list[int] = []

    def _chat(messages, **kwargs):
        calls.append(1)
        import json

        payload = {
            "pages": [
                {
                    "url": page.url,
                    "domain_classification": {"type": "科技/垂直行业媒体", "reason": "blog"},
                    "url_classification": {"type": "普通文章", "reason": "text"},
                },
            ],
        }
        return json.dumps(payload), {}, 10

    with patch(
        "aperix_geo.services.sampling.citation.page_geo.chat_completion",
        side_effect=_chat,
    ):
        out = analyze_citation_pages_geo(
            [page],
            own_brand="Aperix",
            page_brand_scope=[],
            match_terms_by_brand={},
            cache_ttl_s=0,
        )

    assert calls == [1]
    assert out[0]["analysis_source"] == "llm"
    assert out[0]["domain_classification"]["type"] == "科技/垂直行业媒体"
    assert out[0]["url_classification"]["type"] == "普通文章"


def test_analyze_hybrid_when_only_domain_resolved_by_rule() -> None:
    page = _page(
        "https://github.com/org/article",
        domain="github.com",
        text_snippet="generic commentary without code",
    )

    def _chat(messages, **kwargs):
        import json

        payload = {
            "pages": [
                {
                    "url": page.url,
                    "domain_classification": {"type": "其它类型", "reason": "ignored"},
                    "url_classification": {"type": "普通文章", "reason": "text"},
                },
            ],
        }
        return json.dumps(payload), {}, 10

    with patch(
        "aperix_geo.services.sampling.citation.page_geo.chat_completion",
        side_effect=_chat,
    ):
        out = analyze_citation_pages_geo(
            [page],
            own_brand="Aperix",
            page_brand_scope=[],
            match_terms_by_brand={},
            cache_ttl_s=0,
        )

    assert out[0]["analysis_source"] == "hybrid"
    assert out[0]["domain_classification"]["type"] == "代码/开源平台"
    assert out[0]["url_classification"]["type"] == "普通文章"


def test_llm_disabled_uses_rules_only() -> None:
    page = _page(
        "https://github.com/org/repo",
        domain="github.com",
        text_snippet="readme",
    )
    with patch(
        "aperix_geo.services.sampling.citation.page_geo.chat_completion",
    ) as chat:
        out = analyze_citation_pages_geo(
            [page],
            own_brand="Aperix",
            page_brand_scope=[],
            match_terms_by_brand={},
            llm_enabled=False,
        )
    chat.assert_not_called()
    assert out[0]["domain_classification"]["type"] == "代码/开源平台"
    assert out[0]["analysis_source"] == "rule"
