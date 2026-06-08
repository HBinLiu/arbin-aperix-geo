"""Tests for citation page metadata helpers."""

from aperix_geo.utils.html import extract_headings_from_html, html_has_code_block, html_has_table


def test_extract_headings_from_html() -> None:
    html = "<html><body><h1>Main</h1><p>x</p><h2>Sub</h2></body></html>"
    assert extract_headings_from_html(html) == ["Main", "Sub"]


def test_html_has_table_and_code() -> None:
    assert html_has_table("<table><tr><td>1</td></tr></table>") is True
    assert html_has_code_block("<pre><code>print()</code></pre>") is True
    assert html_has_table("<div>no table</div>") is False
