"""Unified page metadata extraction from fetch HTML + Crawl4AI markdown.

Field-level rules (also documented in backend/README.md §页面元数据提取规则
and docs/06-分析指标.md §3.1):

- title / description / keywords / tags / mentions: SEO head + JSON-LD priority chain
- body: prefer rs-trafilatura when available and substantial; else markdown when
  substantial (>= MIN_BODY_CHARS) or when HTML body is insufficient; else HTML
- headings / structure flags: follow the body source when possible
- favicon parsing is intentionally out of scope (see services/favicon/_parse.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from aperix_geo.services.crawl.types import PageFetchResult

from aperix_geo.utils.html import (
    extract_headings_from_html,
    html_has_code_block,
    html_has_table,
    html_to_text,
)
from aperix_geo.services.crawl.seo import (
    SeoMetadata,
    SeoProfile,
    apply_seo_profile,
    parse_seo_from_html,
    profile_include_microdata,
    seo_has_signal,
    seo_prose_text,
)
from aperix_geo.utils.text import coalesce_page_title, headings_from_markdown

HEAD_PARSE_MAX_CHARS = 120_000
MIN_BODY_CHARS = 40

BodySource = Literal["rs", "markdown", "html", "none"]


@dataclass(frozen=True)
class PageMetadata:
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    body_text: str = ""
    has_table: bool = False
    has_code_block: bool = False
    body_source: BodySource = "none"
    url_type: str = ""
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    schema_types: list[str] = field(default_factory=list)
    mentioned_names: list[str] = field(default_factory=list)
    content_type: str = ""
    site_name: str = ""
    canonical_url: str = ""
    authors: list[str] = field(default_factory=list)
    publisher: str = ""
    brand_names: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    faq_items: list[str] = field(default_factory=list)
    speakable_text: list[str] = field(default_factory=list)
    breadcrumbs: list[str] = field(default_factory=list)
    seo_profile: SeoProfile = SeoProfile.FULL

    def has_content(self) -> bool:
        return seo_has_signal(self.seo_metadata(), profile=self.seo_profile) or bool(
            self.body_text.strip(),
        )

    def seo_metadata(self) -> SeoMetadata:
        return SeoMetadata(
            title=self.title,
            description=self.description,
            keywords=tuple(self.keywords),
            tags=tuple(self.tags),
            schema_types=tuple(self.schema_types),
            mentioned_names=tuple(self.mentioned_names),
            content_type=self.content_type,
            site_name=self.site_name,
            canonical_url=self.canonical_url,
            authors=tuple(self.authors),
            publisher=self.publisher,
            brand_names=tuple(self.brand_names),
            categories=tuple(self.categories),
            faq_items=tuple(self.faq_items),
            speakable_text=tuple(self.speakable_text),
            breadcrumbs=tuple(self.breadcrumbs),
        )

    def seo_prose(self, *, max_chars: int = 2000) -> str:
        return seo_prose_text(
            self.seo_metadata(),
            profile=self.seo_profile,
            max_chars=max_chars,
        )


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



def _page_metadata_from_seo(
    seo: SeoMetadata,
    *,
    seo_profile: SeoProfile,
    headings: list[str],
    body_text: str,
    has_table: bool,
    has_code_block: bool,
    body_source: BodySource,
    url_type: str = "",
) -> PageMetadata:
    return PageMetadata(
        title=seo.title,
        description=seo.description,
        headings=headings,
        body_text=body_text,
        has_table=has_table,
        has_code_block=has_code_block,
        body_source=body_source,
        url_type=url_type,
        keywords=list(seo.keywords),
        tags=list(seo.tags),
        schema_types=list(seo.schema_types),
        mentioned_names=list(seo.mentioned_names),
        content_type=seo.content_type,
        site_name=seo.site_name,
        canonical_url=seo.canonical_url,
        authors=list(seo.authors),
        publisher=seo.publisher,
        brand_names=list(seo.brand_names),
        categories=list(seo.categories),
        faq_items=list(seo.faq_items),
        speakable_text=list(seo.speakable_text),
        breadcrumbs=list(seo.breadcrumbs),
        seo_profile=seo_profile,
    )


def extract_page_metadata(
    *,
    html: str = "",
    markdown: str = "",
    url: str = "",
    html_parse_limit: int = HEAD_PARSE_MAX_CHARS,
    body_limit: int | None = None,
    heading_limit: int = 20,
    min_body_chars: int = MIN_BODY_CHARS,
    include_body: bool = True,
    seo_profile: SeoProfile = SeoProfile.FULL,
) -> PageMetadata:
    """Extract page metadata with field-level source rules."""
    return _build_page_metadata(
        html=html,
        markdown=markdown,
        url=url,
        html_parse_limit=html_parse_limit,
        body_limit=body_limit,
        heading_limit=heading_limit,
        min_body_chars=min_body_chars,
        include_body=include_body,
        seo_profile=seo_profile,
    )


def extract_metadata_from_fetch(
    result: PageFetchResult,
    *,
    html_parse_limit: int,
    body_limit: int | None = None,
    heading_limit: int = 20,
    min_body_chars: int = MIN_BODY_CHARS,
    include_body: bool = False,
    seo_profile: SeoProfile = SeoProfile.FULL,
) -> PageMetadata:
    """Extract metadata from an already-fetched page (reuses SEO parse cache)."""
    return _build_page_metadata(
        html=result.html,
        markdown=result.markdown,
        url=result.final_url or "",
        html_parse_limit=html_parse_limit,
        body_limit=body_limit,
        heading_limit=heading_limit,
        min_body_chars=min_body_chars,
        include_body=include_body,
        seo_profile=seo_profile,
    )


def _build_page_metadata(
    *,
    html: str,
    markdown: str,
    url: str,
    html_parse_limit: int,
    body_limit: int | None,
    heading_limit: int,
    min_body_chars: int,
    include_body: bool,
    seo_profile: SeoProfile,
) -> PageMetadata:
    """Extract page metadata with field-level source rules.

    - title / description / SEO fields: HTML head + JSON-LD first, then markdown fallbacks
    - body: prefer ``rs-trafilatura`` when installed and body is substantial; else
      markdown when substantial (>= min_body_chars), else HTML
    - headings / structure flags: markdown when used for body, else HTML
    """
    html_slice = _slice_text(html, html_parse_limit)
    md = markdown or ""
    page_url = (url or "").strip()

    include_microdata = profile_include_microdata(seo_profile)
    seo_raw = (
        parse_seo_from_html(html_slice, include_microdata=include_microdata)
        if html_slice.strip()
        else SeoMetadata()
    )
    seo = apply_seo_profile(seo_raw, seo_profile)

    body_text = ""
    headings: list[str] = []
    has_table = False
    has_code_block = False
    body_source: BodySource = "none"
    url_type = ""

    if include_body:
        md_stripped = md.strip()
        html_body = html_to_text(html_slice, limit=body_limit if body_limit is not None else html_parse_limit)
        html_body_sufficient = len(html_body.strip()) >= min_body_chars
        md_sufficient = len(md_stripped) >= min_body_chars

        if html_slice.strip():
            from aperix_geo.services.url_type.extract import extract_main_content

            rs_body, rs_type = extract_main_content(html_slice, url=page_url)
            if len(rs_body.strip()) >= min_body_chars:
                body_source = "rs"
                body_text = _slice_text(rs_body, body_limit)
                url_type = rs_type
                if md_sufficient:
                    headings = _headings_list_from_markdown(md, limit=heading_limit)
                    has_table = markdown_has_table(md)
                    has_code_block = "```" in md
                else:
                    headings = extract_headings_from_html(html_slice, limit=heading_limit)
                    has_table = html_has_table(html_slice)
                    has_code_block = html_has_code_block(html_slice)

        if body_source == "none":
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

    title = coalesce_page_title(
        seo.title,
        _title_from_markdown(md) if md.strip() else "",
        headings[0][:500] if headings else "",
    )
    if title != seo.title:
        seo = replace(seo, title=title)

    return _page_metadata_from_seo(
        seo,
        seo_profile=seo_profile,
        headings=headings,
        body_text=body_text,
        has_table=has_table,
        has_code_block=has_code_block,
        body_source=body_source,
        url_type=url_type,
    )


def homepage_metadata_dict(parsed: PageMetadata) -> dict[str, str]:
    """Map PageMetadata to competitor homepage metadata fields."""
    h1_h2 = " | ".join(parsed.headings[:6])
    title = parsed.title
    if not title and h1_h2:
        title = h1_h2.split(" | ", 1)[0][:200]
    out = {
        "title": title[:500],
        "description": parsed.description[:2000],
        "h1_h2": h1_h2[:500],
    }
    seo = parsed.seo_prose(max_chars=1500)
    if seo:
        out["seo"] = seo
    return out
