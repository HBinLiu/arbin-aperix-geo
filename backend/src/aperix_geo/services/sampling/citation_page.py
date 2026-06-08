"""Fetch citation source pages and extract metadata for GEO analysis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.html import (
    extract_headings_from_html,
    html_has_code_block,
    html_has_table,
    html_to_text,
    parse_head_from_html,
)
from aperix_geo.utils.text import headings_from_markdown, truncate_text
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import hostname_from_url


@dataclass
class CitationPageMeta:
    url: str
    domain: str
    http_status: int | None = None
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    has_table: bool = False
    has_code_block: bool = False
    text_snippet: str = ""
    fetch_ok: bool = False
    fetch_source: str = "none"

    @property
    def headings_list(self) -> str:
        return " | ".join(self.headings) if self.headings else "（无）"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "domain": self.domain,
            "http_status": self.http_status,
            "title": self.title,
            "description": self.description,
            "headings": list(self.headings),
            "has_table": self.has_table,
            "has_code_block": self.has_code_block,
            "text_snippet": self.text_snippet,
            "fetch_ok": self.fetch_ok,
            "fetch_source": self.fetch_source,
        }


def _primary_domain(url: str) -> str:
    host = (hostname_from_url(url) or "").strip().lower()
    if not host:
        return ""
    return registrable_domain(host) or host


def _headings_from_markdown(markdown: str) -> list[str]:
    text = headings_from_markdown(markdown)
    if not text:
        return []
    return [part.strip() for part in text.split(" | ") if part.strip()]


def _markdown_has_table(markdown: str) -> bool:
    lines = markdown.splitlines()
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
        if "|" in nxt and ("---" in nxt or ":---" in nxt):
            return True
    return False


def fetch_citation_page_meta(
    url: str,
    *,
    crawl: PageCrawlSettings | None = None,
    snippet_chars: int = 4_000,
    max_html_chars: int | None = None,
) -> CitationPageMeta:
    """Fetch a citation URL (httpx → Crawl4AI) and extract structured metadata."""
    key = url.strip()
    domain = _primary_domain(key)
    meta = CitationPageMeta(url=key, domain=domain)
    if not key:
        return meta

    settings = crawl or page_crawl_settings()
    html_limit = max_html_chars if max_html_chars is not None else settings.max_chars

    fetched = fetch_page(key, crawl=settings, max_chars=html_limit)
    meta.http_status = fetched.http_status
    meta.fetch_source = fetched.source

    if not fetched.fetch_ok:
        return meta

    html = fetched.html
    if html:
        title, description = parse_head_from_html(html)
        headings = extract_headings_from_html(html)
        body_text = html_to_text(html, limit=html_limit)
        meta.title = title
        meta.description = description
        meta.headings = headings
        meta.has_table = html_has_table(html)
        meta.has_code_block = html_has_code_block(html)
        meta.text_snippet = truncate_text(body_text, snippet_chars) if body_text else ""
    elif fetched.markdown:
        headings = _headings_from_markdown(fetched.markdown)
        meta.title = headings[0] if headings else ""
        meta.headings = headings
        meta.has_table = _markdown_has_table(fetched.markdown)
        meta.has_code_block = "```" in fetched.markdown
        meta.text_snippet = truncate_text(fetched.markdown, snippet_chars)

    meta.fetch_ok = bool(meta.text_snippet or meta.title or meta.description)
    return meta


def fetch_citation_pages_parallel(
    urls: list[str],
    *,
    crawl: PageCrawlSettings | None = None,
    snippet_chars: int = 4_000,
    max_html_chars: int | None = None,
    concurrency: int | None = None,
) -> list[CitationPageMeta]:
    """Fetch multiple citation URLs concurrently; output order matches input."""
    if not urls:
        return []

    settings = crawl or page_crawl_settings()
    if len(urls) == 1:
        return [
            fetch_citation_page_meta(
                urls[0],
                crawl=settings,
                snippet_chars=snippet_chars,
                max_html_chars=max_html_chars,
            ),
        ]

    workers = min(len(urls), max(1, concurrency if concurrency is not None else settings.concurrency))

    def _fetch_one(url: str) -> CitationPageMeta:
        return fetch_citation_page_meta(
            url,
            crawl=settings,
            snippet_chars=snippet_chars,
            max_html_chars=max_html_chars,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_fetch_one, urls))


def page_mentions_any_term(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for term in terms:
        needle = (term or "").strip().lower()
        if needle and needle in lowered:
            return True
    return False
