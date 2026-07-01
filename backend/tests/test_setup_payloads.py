"""Tests for Setup LLM payload builders."""

from aperix_geo.services.setup.llm.payloads import build_subject_research_payload


def test_build_domain_research_payload_site_data() -> None:
    payload = build_subject_research_payload(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="https://example.com",
        homepage_text="首页正文",
        homepage_metadata={
            "title": "示例",
            "description": "描述",
            "h1_h2": "产品 | 解决方案",
            "seo": "keywords: GEO, SaaS",
        },
    )
    assert payload["mode"] == "domain"
    site_data = payload["site_data"]
    assert site_data["title"] == "示例"
    assert site_data["homepage_excerpt"] == "首页正文"
    assert site_data["seo"] == "keywords: GEO, SaaS"
    assert "extra_pages" not in site_data
