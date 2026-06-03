"""Tests for HTML helpers."""

from aperix_geo.utils.html import html_to_text, parse_head_from_html


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


def test_html_to_text_strips_tags() -> None:
    html = "<html><script>ignore()</script><body><p>Hello</p> world</body></html>"
    assert html_to_text(html, limit=100) == "Hello world"
