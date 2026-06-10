"""Fetch citation source pages and extract metadata for GEO analysis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from uuid import UUID

from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl.metadata import extract_page_metadata
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.text import truncate_text
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

    @classmethod
    def from_dict(cls, data: dict) -> CitationPageMeta:
        return cls(
            url=str(data.get("url") or ""),
            domain=str(data.get("domain") or ""),
            http_status=data.get("http_status"),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            headings=list(data.get("headings") or []),
            has_table=bool(data.get("has_table")),
            has_code_block=bool(data.get("has_code_block")),
            text_snippet=str(data.get("text_snippet") or ""),
            fetch_ok=bool(data.get("fetch_ok")),
            fetch_source=str(data.get("fetch_source") or "none"),
        )


def _primary_domain(url: str) -> str:
    host = (hostname_from_url(url) or "").strip().lower()
    if not host:
        return ""
    return registrable_domain(host) or host


def fetch_citation_page_meta(
    url: str,
    *,
    crawl: PageCrawlSettings | None = None,
    snippet_chars: int = 4_000,
    max_html_chars: int | None = None,
    sampling_job_id: UUID | None = None,
) -> CitationPageMeta:
    """Fetch a citation URL (httpx → Crawl4AI) and extract structured metadata."""
    from aperix_geo.services.sampling.citation.cache.page_meta import (
        get_job_citation_page,
        set_job_citation_page,
    )

    key = url.strip()
    domain = _primary_domain(key)
    if not key:
        return CitationPageMeta(url=key, domain=domain)

    if sampling_job_id is not None:
        cached = get_job_citation_page(sampling_job_id, key)
        if cached is not None:
            return CitationPageMeta.from_dict(cached)

    meta = CitationPageMeta(url=key, domain=domain)

    settings = crawl or page_crawl_settings()
    html_limit = max_html_chars if max_html_chars is not None else settings.max_chars

    fetched = fetch_page(key, crawl=settings, max_chars=html_limit)
    meta.http_status = fetched.http_status
    meta.fetch_source = fetched.source

    if not fetched.fetch_ok:
        if sampling_job_id is not None:
            set_job_citation_page(sampling_job_id, meta.to_dict())
        return meta

    parsed = extract_page_metadata(
        html=fetched.html,
        markdown=fetched.markdown,
        html_parse_limit=html_limit,
        body_limit=html_limit,
    )
    meta.title = parsed.title
    meta.description = parsed.description
    meta.headings = list(parsed.headings)
    meta.has_table = parsed.has_table
    meta.has_code_block = parsed.has_code_block
    meta.text_snippet = truncate_text(parsed.body_text, snippet_chars) if parsed.body_text else ""
    meta.fetch_ok = parsed.has_content()

    if sampling_job_id is not None:
        set_job_citation_page(sampling_job_id, meta.to_dict())
    return meta


def fetch_citation_pages_parallel(
    urls: list[str],
    *,
    crawl: PageCrawlSettings | None = None,
    snippet_chars: int = 4_000,
    max_html_chars: int | None = None,
    concurrency: int | None = None,
    sampling_job_id: UUID | None = None,
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
                sampling_job_id=sampling_job_id,
            ),
        ]

    workers = min(len(urls), max(1, concurrency if concurrency is not None else settings.concurrency))

    def _fetch_one(url: str) -> CitationPageMeta:
        return fetch_citation_page_meta(
            url,
            crawl=settings,
            snippet_chars=snippet_chars,
            max_html_chars=max_html_chars,
            sampling_job_id=sampling_job_id,
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
