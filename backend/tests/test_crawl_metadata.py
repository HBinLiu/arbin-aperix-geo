"""Tests for unified page metadata extraction."""

from aperix_geo.services.crawl.metadata import (
    extract_metadata_from_fetch,
    extract_page_metadata,
    homepage_metadata_dict,
    markdown_has_table,
)
from aperix_geo.services.crawl.types import PageFetchResult


def test_head_from_html_only() -> None:
    html = """
    <html><head>
    <title>站点标题</title>
    <meta name="description" content="站点描述" />
    </head><body><h1>正文标题</h1><p>内容</p></body></html>
    """
    parsed = extract_page_metadata(html=html)
    assert parsed.title == "站点标题"
    assert parsed.description == "站点描述"
    assert parsed.body_source == "html"
    assert "正文标题" in parsed.body_text
    assert parsed.headings == ["正文标题"]


def test_markdown_preferred_when_both_present() -> None:
    html = "<head><title>HTML Title</title></head><body><nav>noise</nav><p>html body</p></body>"
    md = "# MD Title\n\nClean markdown body " * 5
    parsed = extract_page_metadata(html=html, markdown=md)
    assert parsed.title == "HTML Title"
    assert parsed.body_source == "markdown"
    assert parsed.body_text.startswith("# MD Title")
    assert parsed.headings == ["MD Title"]
    assert parsed.has_code_block is False


def test_markdown_only_fallback() -> None:
    md = "# Only MD\n\nShort"  # below MIN_BODY_CHARS
    parsed = extract_page_metadata(markdown=md)
    assert parsed.title == "Only MD"
    assert parsed.body_source == "markdown"
    assert "Short" in parsed.body_text


def test_title_fallback_from_markdown_when_no_html_head() -> None:
    parsed = extract_page_metadata(markdown="# Fallback Title\n\nBody text " * 10)
    assert parsed.title == "Fallback Title"
    assert parsed.body_source == "markdown"


def test_homepage_metadata_dict() -> None:
    html = "<head><title>深睿医疗</title><meta name=description content='AI辅助诊断'></head>"
    md = "# 用AI赋能\n\n## 改变未来"
    parsed = extract_page_metadata(html=html, markdown=md)
    meta = homepage_metadata_dict(parsed)
    assert meta["title"] == "深睿医疗"
    assert meta["description"] == "AI辅助诊断"
    assert meta["h1_h2"] == "用AI赋能 | 改变未来"


def test_include_body_false_skips_body() -> None:
    md = "# Title\n\n" + ("body " * 50)
    parsed = extract_page_metadata(html="", markdown=md, include_body=False)
    assert parsed.title == "Title"
    assert parsed.body_text == ""
    assert parsed.body_source == "none"
    assert parsed.headings == []


def test_markdown_has_table() -> None:
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    assert markdown_has_table(md) is True
    assert markdown_has_table("# no table") is False


def test_has_content() -> None:
    assert extract_page_metadata(html="<title>T</title>").has_content() is True
    html = """
    <head><meta name="keywords" content="GEO, SaaS" /></head>
    """
    assert extract_page_metadata(html=html).has_content() is True
    assert extract_page_metadata().has_content() is False


def test_extract_metadata_from_fetch_reuses_seo_cache() -> None:
    from aperix_geo.services.crawl.seo import clear_seo_parse_cache

    clear_seo_parse_cache()
    html = "<head><title>Fetch Title</title><meta name='description' content='desc' /></head>"
    result = PageFetchResult(url="https://x.com", html=html, source="httpx")
    assert result.fetch_ok is True
    parsed = extract_metadata_from_fetch(result, html_parse_limit=64_000, include_body=False)
    assert parsed.title == "Fetch Title"
    assert parsed.description == "desc"


def test_template_title_falls_back_to_og_title() -> None:
    html = """
    <html><head>
    <title>{{content.leadTitle}}</title>
    <meta property="og:title" content="真实文章标题" />
    </head></html>
    """
    parsed = extract_page_metadata(html=html)
    assert parsed.title == "真实文章标题"


def test_template_title_falls_back_to_markdown_heading() -> None:
    html = "<head/><head><title>{{content.leadTitle}}</title></head>"
    md = "# Markdown 页面标题\n\n正文内容 " * 5
    parsed = extract_page_metadata(html=html, markdown=md)
    assert parsed.title == "Markdown 页面标题"
