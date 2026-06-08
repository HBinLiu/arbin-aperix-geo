"""HTML text extraction helpers."""

from __future__ import annotations

import html as html_lib
import re

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']*)["\']'
    r'|<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_TABLE_RE = re.compile(r"<table\b", re.IGNORECASE)
_CODE_BLOCK_RE = re.compile(
    r"<(?:pre|code)\b|```",
    re.IGNORECASE,
)


def _normalize_text(raw: str, *, limit: int | None = None) -> str:
    text = html_lib.unescape(re.sub(r"\s+", " ", raw)).strip()
    if limit is not None:
        return text[:limit]
    return text


def parse_head_from_html(html: str) -> tuple[str, str]:
    title = ""
    description = ""
    if m := _TITLE_RE.search(html):
        title = _normalize_text(m.group(1), limit=500)
    if m := _META_DESC_RE.search(html):
        description = _normalize_text(m.group(1) or m.group(2) or "", limit=2000)
    return title, description


def html_to_text(html: str, *, limit: int | None = None) -> str:
    cleaned = _TAG_RE.sub(" ", html)
    text = _TAG_STRIP_RE.sub(" ", cleaned)
    return _normalize_text(text, limit=limit)


def extract_headings_from_html(html: str, *, limit: int = 20) -> list[str]:
    headings: list[str] = []
    for match in _HEADING_RE.finditer(html or ""):
        text = _normalize_text(_TAG_STRIP_RE.sub(" ", match.group(2)), limit=300)
        if text:
            headings.append(text)
        if len(headings) >= limit:
            break
    return headings


def html_has_table(html: str) -> bool:
    return bool(_TABLE_RE.search(html or ""))


def html_has_code_block(html: str) -> bool:
    return bool(_CODE_BLOCK_RE.search(html or ""))
