"""Unified page metadata extraction from fetch HTML + Crawl4AI markdown.

Field-level rules (also documented in backend/README.md §页面元数据提取规则
and docs/06-分析指标.md §3.1):

- title / description: HTML head (BeautifulSoup) → markdown heading / first line
- body / headings / structure flags: prefer markdown when substantial (>= MIN_BODY_CHARS)
  or when HTML body is insufficient; else HTML extraction
- favicon parsing is intentionally out of scope (see services/favicon/_parse.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from aperix_geo.utils.html import (
    extract_headings_from_html,
    html_has_code_block,
    html_has_table,
    html_to_text,
    parse_head_from_html,
)
from aperix_geo.utils.text import headings_from_markdown

HEAD_PARSE_MAX_CHARS = 120_000
MIN_BODY_CHARS = 40

BodySource = Literal["markdown", "html", "none"]


@dataclass(frozen=True)
class PageMetadata:
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    body_text: str = ""
    has_table: bool = False
    has_code_block: bool = False
    body_source: BodySource = "none"

    def has_content(self) -> bool:
        return bool(self.body_text.strip() or self.title or self.description)


def _slice_text(text: str, limit: int | None) -> str:
    if not text or limit is None:
        return text
    return text[:limit]


def _headings_list_from_markdown(markdown: str, *, limit: int) -> list[str]:
    joined = headings_from_markdown(markdown, limit=limit)
    if not joined:
        return []
    return [part.strip() for part in joined.split(" | ") if part.strip()]


def _title_from_markdown(markdown: str) -> str:
    headings = headings_from_markdown(markdown, limit=1)
    if headings:
        return headings.split(" | ", 1)[0][:500]
    first = markdown.strip().split("\n", 1)[0].lstrip("# ").strip()
    return first[:500] if first else ""


def markdown_has_table(markdown: str) -> bool:
    lines = markdown.splitlines()
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
        if "|" in nxt and ("---" in nxt or ":---" in nxt):
            return True
    return False


def extract_page_metadata(
    *,
    html: str = "",
    markdown: str = "",
    html_parse_limit: int = HEAD_PARSE_MAX_CHARS,
    body_limit: int | None = None,
    heading_limit: int = 20,
    min_body_chars: int = MIN_BODY_CHARS,
    include_body: bool = True,
) -> PageMetadata:
    """Extract page metadata with field-level source rules.

    - title / description: HTML head first, then markdown heading / first line
    - body / headings / structure flags: markdown when substantial (>= min_body_chars),
      else HTML; short markdown used only when HTML body is unavailable
    """
    html_slice = _slice_text(html, html_parse_limit)
    md = markdown or ""

    title = ""
    description = ""
    if html_slice.strip():
        title, description = parse_head_from_html(html_slice)
    if not title and md.strip():
        title = _title_from_markdown(md)

    body_text = ""
    headings: list[str] = []
    has_table = False
    has_code_block = False
    body_source: BodySource = "none"

    if include_body:
        md_stripped = md.strip()
        html_body = html_to_text(html_slice, limit=body_limit if body_limit is not None else html_parse_limit)
        html_body_sufficient = len(html_body.strip()) >= min_body_chars
        md_sufficient = len(md_stripped) >= min_body_chars
        use_markdown = md_sufficient or (bool(md_stripped) and not html_body_sufficient)

        if use_markdown:
            body_source = "markdown"
            body_text = _slice_text(md_stripped, body_limit)
            headings = _headings_list_from_markdown(md, limit=heading_limit)
            has_table = markdown_has_table(md)
            has_code_block = "```" in md
        elif html_slice.strip():
            body_source = "html"
            body_text = html_body
            headings = extract_headings_from_html(html_slice, limit=heading_limit)
            has_table = html_has_table(html_slice)
            has_code_block = html_has_code_block(html_slice)

    if not title and headings:
        title = headings[0][:500]

    return PageMetadata(
        title=title,
        description=description,
        headings=headings,
        body_text=body_text,
        has_table=has_table,
        has_code_block=has_code_block,
        body_source=body_source,
    )


def homepage_metadata_dict(parsed: PageMetadata) -> dict[str, str]:
    """Map PageMetadata to competitor homepage metadata fields."""
    h1_h2 = " | ".join(parsed.headings[:6])
    title = parsed.title
    if not title and h1_h2:
        title = h1_h2.split(" | ", 1)[0][:200]
    return {
        "title": title[:500],
        "description": parsed.description[:2000],
        "h1_h2": h1_h2[:500],
    }
