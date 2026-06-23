"""Fetch citation source pages and extract metadata."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from uuid import UUID

from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl.metadata import SeoProfile, extract_page_metadata
from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.services.crawl.types import PageFetchResult
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight
from aperix_geo.utils.net import citation_from, filter_citation_urls, host_from, is_citation_host
from aperix_geo.utils.net import crawl_cache_url


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
    schema_types: list[str] = field(default_factory=list)
    content_type: str = ""
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
            "schema_types": list(self.schema_types),
            "content_type": self.content_type,
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
            schema_types=list(data.get("schema_types") or []),
            content_type=str(data.get("content_type") or ""),
            fetch_ok=bool(data.get("fetch_ok")),
            fetch_source=str(data.get("fetch_source") or "none"),
        )


def _primary_domain(url: str) -> str:
    return citation_from(url)


def _citation_url_priority(url: str, *, own_root: str | None, competitor_roots: set[str]) -> tuple[int, str]:
    host = _primary_domain(url)
    if own_root and host == own_root:
        return (0, url)
    if host in competitor_roots:
        return (1, url)
    return (2, url)


def sort_citation_urls_for_fetch(
    urls: list[str],
    *,
    own_root: str | None = None,
    competitor_roots: set[str] | None = None,
) -> list[str]:
    """Own and competitor URLs first; preserve stable order within each tier."""
    roots = competitor_roots or set()
    return sorted(
        dict.fromkeys(urls),
        key=lambda url: _citation_url_priority(url, own_root=own_root, competitor_roots=roots),
    )


def _read_cached_page_fetch(
    url: str,
    *,
    settings: PageCrawlSettings,
    html_limit: int,
) -> PageFetchResult | None:
    """Return cached page fetch (positive or negative) when HTML layer has an entry."""
    if settings.cache_ttl_s <= 0 and settings.negative_cache_ttl_s <= 0:
        return None
    from aperix_geo.services.crawl._cache import get_cached_page

    return get_cached_page(
        url,
        max_chars=html_limit,
        crawl_fallback=settings.crawl_fallback,
        ttl_s=settings.cache_ttl_s,
        negative_ttl_s=settings.negative_cache_ttl_s,
    )


def _citation_meta_from_fetch(
    url: str,
    *,
    domain: str,
    fetched: PageFetchResult,
    snippet_chars: int,
    html_limit: int,
) -> CitationPageMeta:
    meta = CitationPageMeta(url=url, domain=domain)
    meta.http_status = fetched.http_status
    meta.fetch_source = fetched.source

    if not fetched.fetch_ok:
        return meta

    parsed = extract_page_metadata(
        html=fetched.html,
        markdown=fetched.markdown,
        html_parse_limit=html_limit,
        body_limit=html_limit,
        seo_profile=SeoProfile.CITATION,
    )
    meta.title = parsed.title
    meta.description = parsed.description
    meta.headings = list(parsed.headings)
    meta.has_table = parsed.has_table
    meta.has_code_block = parsed.has_code_block
    snippet_parts: list[str] = []
    seo = parsed.seo_prose(max_chars=min(1500, snippet_chars))
    if seo:
        snippet_parts.append(seo)
    if parsed.body_text:
        snippet_parts.append(parsed.body_text)
    meta.text_snippet = truncate_text("\n\n".join(snippet_parts), snippet_chars) if snippet_parts else ""
    meta.schema_types = list(parsed.schema_types)
    meta.content_type = parsed.content_type
    meta.fetch_ok = parsed.has_content()

    if meta.fetch_ok and fetched.html.strip():
        from aperix_geo.services.favicon._citation import cache_citation_favicon_from_page_html

        cache_citation_favicon_from_page_html(
            page_url=fetched.final_url or url,
            html=fetched.html,
        )
    return meta


def _persist_citation_meta(
    meta: CitationPageMeta,
    *,
    sampling_job_id: UUID | None,
) -> None:
    from aperix_geo.services.sampling.citation.cache.page_meta import set_job_citation_page
    from aperix_geo.services.sampling.citation.cache.url_meta import set_url_citation_page

    if sampling_job_id is not None:
        set_job_citation_page(sampling_job_id, meta.to_dict())
    if meta.fetch_ok:
        set_url_citation_page(meta.to_dict())


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
    host = host_from(key)
    if not key or not is_citation_host(host):
        return CitationPageMeta(url=key, domain=domain)

    if sampling_job_id is not None:
        cached = get_job_citation_page(sampling_job_id, key)
        if cached is not None:
            return CitationPageMeta.from_dict(cached)

    from aperix_geo.services.sampling.citation.cache.url_meta import (
        get_url_citation_page,
        set_url_citation_page,
    )

    url_cached = get_url_citation_page(key)
    if url_cached is not None:
        meta = CitationPageMeta.from_dict(url_cached)
        if sampling_job_id is not None:
            set_job_citation_page(sampling_job_id, meta.to_dict())
        return meta

    settings = crawl or page_crawl_settings()
    html_limit = max_html_chars if max_html_chars is not None else settings.max_chars

    cached_page = _read_cached_page_fetch(key, settings=settings, html_limit=html_limit)
    if cached_page is not None:
        meta = _citation_meta_from_fetch(
            key,
            domain=domain,
            fetched=cached_page,
            snippet_chars=snippet_chars,
            html_limit=html_limit,
        )
        _persist_citation_meta(meta, sampling_job_id=sampling_job_id)
        return meta

    def _read_job_cache() -> CitationPageMeta | None:
        if sampling_job_id is None:
            return None
        cached_row = get_job_citation_page(sampling_job_id, key)
        if cached_row is None:
            return None
        return CitationPageMeta.from_dict(cached_row)

    def _fetch_and_parse() -> CitationPageMeta:
        fetched = fetch_page(key, crawl=settings, max_chars=html_limit)
        meta = _citation_meta_from_fetch(
            key,
            domain=domain,
            fetched=fetched,
            snippet_chars=snippet_chars,
            html_limit=html_limit,
        )
        _persist_citation_meta(meta, sampling_job_id=sampling_job_id)
        return meta

    if sampling_job_id is None:
        return _fetch_and_parse()

    wait_s = settings.fetch_timeout_s + settings.crawl_timeout_s + 15.0
    flight_key = f"{sampling_job_id}:{crawl_cache_url(key)}"
    try:
        return run_single_flight(
            flight_key,
            wait_s=wait_s,
            read_cache=_read_job_cache,
            fetch=_fetch_and_parse,
            lock_prefix="aperix:sampling:job_page_fetch:",
        )
    except SingleFlightWaitTimeout:
        cached = _read_job_cache()
        if cached is not None:
            return cached
        return _fetch_and_parse()


def fetch_citation_pages_parallel(
    urls: list[str],
    *,
    crawl: PageCrawlSettings | None = None,
    snippet_chars: int = 4_000,
    max_html_chars: int | None = None,
    concurrency: int | None = None,
    sampling_job_id: UUID | None = None,
    own_root: str | None = None,
    competitor_roots: set[str] | None = None,
) -> list[CitationPageMeta]:
    """Fetch multiple citation URLs concurrently; output order matches input."""
    ordered = sort_citation_urls_for_fetch(
        urls,
        own_root=own_root,
        competitor_roots=competitor_roots,
    )
    if not ordered:
        return []

    settings = crawl or page_crawl_settings()
    if len(ordered) == 1:
        return [
            fetch_citation_page_meta(
                ordered[0],
                crawl=settings,
                snippet_chars=snippet_chars,
                max_html_chars=max_html_chars,
                sampling_job_id=sampling_job_id,
            ),
        ]

    workers = min(len(ordered), max(1, concurrency if concurrency is not None else settings.concurrency))
    original_index = {url: index for index, url in enumerate(urls)}

    def _fetch_one(url: str) -> tuple[int, CitationPageMeta]:
        meta = fetch_citation_page_meta(
            url,
            crawl=settings,
            snippet_chars=snippet_chars,
            max_html_chars=max_html_chars,
            sampling_job_id=sampling_job_id,
        )
        return original_index.get(url, len(urls)), meta

    with ThreadPoolExecutor(max_workers=workers) as pool:
        indexed = list(pool.map(_fetch_one, ordered))
    indexed.sort(key=lambda item: item[0])
    return [meta for _index, meta in indexed]


def page_mentions_any_term(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for term in terms:
        needle = (term or "").strip().lower()
        if needle and needle in lowered:
            return True
    return False


def page_mentioned_brands_from_snippet(
    page: CitationPageMeta,
    *,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
) -> list[str]:
    """Match page_brand_scope against text_snippet (case-insensitive substring + alias terms)."""
    if not page_brand_scope:
        return []
    if page.http_status is not None and page.http_status != 200:
        return []
    if not page.fetch_ok or not (page.text_snippet or "").strip():
        return []
    mentioned: list[str] = []
    for brand in page_brand_scope:
        terms = match_terms_by_brand.get(brand, [brand])
        if page_mentions_any_term(page.text_snippet, terms) and brand not in mentioned:
            mentioned.append(brand)
    return mentioned
