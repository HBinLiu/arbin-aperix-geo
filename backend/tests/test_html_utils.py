"""Tests for HTML helpers."""

from aperix_geo.utils.html import (
    extract_headings_from_html,
    html_to_text,
    parse_head_from_html,
)


def test_parse_head_from_html() -> None:
    html = """
    <html><head>
    <title>  万里汇 | 官网  </title>
    <meta name="description" content="跨境支付平台" />
    </head><body></body></html>
    """
    title, description = parse_head_from_html(html)
    assert title == "万里汇 | 官网"
    assert description == "跨境支付平台"


def test_parse_head_meta_content_before_name() -> None:
    html = """
    <head>
    <meta content="乱序描述" name="description" />
    </head>
    """
    _, description = parse_head_from_html(html)
    assert description == "乱序描述"


def test_parse_head_og_description_fallback() -> None:
    html = """
    <head>
    <meta property="og:description" content="OG 描述" />
    </head>
    """
    _, description = parse_head_from_html(html)
    assert description == "OG 描述"


def test_parse_head_og_title_fallback() -> None:
    html = """
    <head>
    <meta property="og:title" content="OG 标题" />
    </head>
    """
    title, _ = parse_head_from_html(html)
    assert title == "OG 标题"


def test_parse_head_title_over_og_title() -> None:
    html = """
    <head>
    <title>页面标题</title>
    <meta property="og:title" content="OG 标题" />
    </head>
    """
    title, _ = parse_head_from_html(html)
    assert title == "页面标题"


def test_parse_head_title_with_nested_tags() -> None:
    html = "<head><title>Foo <span>Bar</span></title></head>"
    title, _ = parse_head_from_html(html)
    assert title == "Foo Bar"


def test_parse_head_html_entities() -> None:
    html = '<head><title>A &amp; B</title></head>'
    title, _ = parse_head_from_html(html)
    assert title == "A & B"


def test_parse_head_malformed_html() -> None:
    html = "<head><title>仍可读</title><meta name=description content=无引号></head>"
    title, description = parse_head_from_html(html)
    assert title == "仍可读"
    assert description == "无引号"


def test_parse_head_empty() -> None:
    assert parse_head_from_html("") == ("", "")
    assert parse_head_from_html("   ") == ("", "")


def test_html_to_text_strips_tags() -> None:
    html = "<html><script>ignore()</script><body><p>Hello</p> world</body></html>"
    assert html_to_text(html, limit=100) == "Hello world"


def test_html_to_text_empty() -> None:
    assert html_to_text("") == ""


def test_extract_headings_nested_and_order() -> None:
    html = "<body><h1>Main <em>emph</em></h1><h2>Sub</h2></body>"
    assert extract_headings_from_html(html) == ["Main emph", "Sub"]
