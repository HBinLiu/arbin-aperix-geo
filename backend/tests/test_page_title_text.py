"""Page title sanitization and mojibake repair."""

from __future__ import annotations

from aperix_geo.utils.text import (
    coalesce_page_title,
    is_garbled_page_title,
    repair_utf8_mojibake,
    sanitize_page_title,
)


def test_repair_utf8_mojibake_recovers_chinese_title() -> None:
    original = "2026年高端红茶品牌推荐"
    garbled = original.encode("utf-8").decode("latin-1")
    assert garbled != original
    assert repair_utf8_mojibake(garbled) == original


def test_sanitize_page_title_rejects_garbled_text() -> None:
    garbled = "2026\uFFFD3a\uFFFD\uFFFD..."
    assert sanitize_page_title(garbled) == ""


def test_coalesce_page_title_falls_back_to_url_for_garbled_title() -> None:
    url = "https://example.com/article"
    garbled = "2026\uFFFD3a\uFFFD\uFFFD..."
    assert coalesce_page_title(garbled, url=url) == url


def test_coalesce_page_title_keeps_valid_title() -> None:
    title = "礼品采购者如何判断红茶品牌信誉？"
    assert not is_garbled_page_title(title)
    assert coalesce_page_title(title, url="https://example.com") == title
