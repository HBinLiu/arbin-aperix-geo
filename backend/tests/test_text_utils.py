"""Tests for text helpers."""

from aperix_geo.utils.text import headings_from_markdown, normalize_whitespace, prompt_text_hash, truncate_text


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("  hello   world \n") == "hello world"


def test_truncate_text() -> None:
    out = truncate_text("x" * 100, 50)
    assert "截断" in out
    assert len(out) == 50


def test_prompt_text_hash_normalizes_whitespace() -> None:
    assert prompt_text_hash("  a  b ") == prompt_text_hash("a b")


def test_headings_from_markdown() -> None:
    md = "# Title\n\n## Sub\n\n### Skip extra"
    assert headings_from_markdown(md, limit=2) == "Title | Sub"
