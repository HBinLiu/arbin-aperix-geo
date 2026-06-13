"""HTML text extraction helpers (BeautifulSoup + html.parser)."""

from __future__ import annotations

import html as html_lib
import re

from bs4 import BeautifulSoup, SoupStrainer

_HEAD_STRAINER = SoupStrainer(["title", "meta"])
_TABLE_STRAINER = SoupStrainer("table")
_CODE_STRAINER = SoupStrainer(["pre", "code"])
_DESC_META_KEYS = ("description", "og:description")
_TITLE_FALLBACK_KEYS = ("og:title",)
_CODE_FENCE_RE = re.compile(r"```")
_STRIP_TAGS = ("script", "style", "noscript")


def _normalize_text(raw: str, *, limit: int | None = None) -> str:
    text = html_lib.unescape(re.sub(r"\s+", " ", raw)).strip()
    if limit is not None:
        return text[:limit]
    return text


def _meta_content(soup: BeautifulSoup, *keys: str) -> str:
    for key in keys:
        for attr in ("name", "property"):
            tag = soup.find("meta", attrs={attr: key})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()
    return ""


def parse_head_from_html(html: str) -> tuple[str, str]:
    """Return best-effort title and description (SEO/GEO meta priority chain)."""
    from aperix_geo.services.crawl.seo import parse_seo_from_html

    seo = parse_seo_from_html(html)
    return seo.title, seo.description


def html_to_text(html: str, *, limit: int | None = None) -> str:
    if not (html or "").strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return _normalize_text(text, limit=limit)


def extract_headings_from_html(html: str, *, limit: int = 20) -> list[str]:
    if not (html or "").strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    headings: list[str] = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$", re.I)):
        text = _normalize_text(tag.get_text(separator=" ", strip=True), limit=300)
        if text:
            headings.append(text)
        if len(headings) >= limit:
            break
    return headings


def html_has_table(html: str) -> bool:
    if not (html or "").strip():
        return False
    soup = BeautifulSoup(html, "html.parser", parse_only=_TABLE_STRAINER)
    return soup.find("table") is not None


def html_has_code_block(html: str) -> bool:
    if _CODE_FENCE_RE.search(html or ""):
        return True
    if not (html or "").strip():
        return False
    soup = BeautifulSoup(html, "html.parser", parse_only=_CODE_STRAINER)
    return soup.find(["pre", "code"]) is not None
