"""Citation URL resolution: page fetch, source metadata, brand mention detection."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.citation.document import CitationDocument
from aperix_geo.services.sampling.citation.labels import brand_names_match, page_mentioned_brand_names
from aperix_geo.services.sampling.citation.page import (
    CitationPageMeta,
    fetch_citation_pages_parallel,
    page_mentioned_brands_from_snippet,
)
from aperix_geo.services.sampling.citation.scope import (
    citation_brand_scope,
    citation_match_terms_by_brand,
)
from aperix_geo.services.sampling.mentions import CompetitorEntry, collect_match_terms
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft
from aperix_geo.utils.net import (
    filter_citation_urls,
    host_from,
    host_under_root,
    registrable_from,
)

if TYPE_CHECKING:
    from aperix_geo.services.crawl.settings import PageCrawlSettings


def citation_root(subject: Subject) -> str | None:
    if subject.website_url:
        root = registrable_from(subject.website_url)
        if root:
            return root
    if subject.type == SubjectType.domain and subject.domain:
        root = registrable_from(subject.domain) or host_from(subject.domain)
        return root or None
    return None


def _url_matches_competitor(url: str, entry: CompetitorEntry) -> bool:
    if not entry.domain:
        return False
    root = registrable_from(entry.domain) or host_from(entry.domain)
    if not root:
        return False
    return host_under_root(host_from(url), root)


def _url_target(url: str, *, root: str | None, competitors: list[CompetitorEntry]) -> str:
    if root and host_under_root(host_from(url), root):
        return "own"
    for entry in competitors:
        if _url_matches_competitor(url, entry):
            return entry.label
    return ""


def _load_cached_page_meta(url: str, sampling_job_id: UUID | None) -> CitationPageMeta | None:
    from aperix_geo.services.sampling.citation.cache.page_meta import get_job_citation_page
    from aperix_geo.services.sampling.citation.cache.url_meta import get_url_citation_page

    key = url.strip()
    cached = None
    if sampling_job_id is not None:
        cached = get_job_citation_page(sampling_job_id, key)
    if cached is None:
        cached = get_url_citation_page(key)
    if cached is None:
        return None
    return CitationPageMeta.from_dict(cached)


def fetch_citation_pages_for_urls(
    urls: list[str],
    *,
    crawl: "PageCrawlSettings",
    snippet_chars: int,
    sampling_job_id: UUID | None = None,
    own_root: str | None = None,
    competitor_roots: set[str] | None = None,
) -> list[CitationPageMeta]:
    """Fetch citation source pages (IO-bound; safe to run parallel to ABSA)."""
    safe_urls = filter_citation_urls(list(urls))
    if not safe_urls:
        return []

    pages_by_url: dict[str, CitationPageMeta] = {}
    missing: list[str] = []
    for url in safe_urls:
        cached = _load_cached_page_meta(url, sampling_job_id)
        if cached is not None:
            pages_by_url[url] = cached
        else:
            missing.append(url)

    if missing:
        fetched = fetch_citation_pages_parallel(
            missing,
            crawl=crawl,
            snippet_chars=snippet_chars,
            sampling_job_id=sampling_job_id,
            own_root=own_root,
            competitor_roots=competitor_roots,
        )
        for meta in fetched:
            pages_by_url[meta.url] = meta

    return [
        pages_by_url.get(url) or CitationPageMeta(url=url, domain=registrable_from(url))
        for url in safe_urls
    ]


def build_citation_document(
    pages: list[CitationPageMeta],
    urls: list[str],
    *,
    root: str | None,
    own_names: list[str],
    own_brand: str,
    competitors: list[CompetitorEntry],
    entity_signals: list[EntitySignalDraft],
    open_brand_labels: list[str] | None = None,
) -> CitationDocument:
    """Assemble citation document from pre-fetched pages."""
    page_brand_scope = citation_brand_scope(
        entity_signals,
        own_brand=own_brand,
        competitors=competitors,
        open_brand_labels=open_brand_labels,
    )
    match_terms = citation_match_terms_by_brand(
        page_brand_scope,
        own_brand=own_brand,
        own_names=own_names,
        competitors=competitors,
    )
    own_brand_keys = collect_match_terms(own_brand, *own_names)
    citation_urls_own = [url for url in urls if root and host_under_root(host_from(url), root)]

    citation_sources: list[dict] = []
    for page in pages:
        page_analysis = {
            "page_mentioned_brands": page_mentioned_brands_from_snippet(
                page,
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms,
            ),
        }
        target = _url_target(page.url, root=root, competitors=competitors)
        page_mentioned = page_mentioned_brand_names(page_analysis)

        citation_sources.append(
            {
                "url": page.url,
                "domain": page.domain,
                "http_status": page.http_status,
                "page_title": page.title,
                "site_name": page.site_name,
                "description": page.description,
                "headings": page.headings,
                "has_table": page.has_table,
                "has_code_block": page.has_code_block,
                "text_snippet": page.text_snippet,
                "fetch_ok": page.fetch_ok,
                "url_type": page.url_type,
                "target": target,
                "page_mentions_brand": target == "own" and brand_names_match(own_brand_keys, page_mentioned),
                "llm_analysis": page_analysis,
            }
        )

    return CitationDocument(
        citation_urls_own=citation_urls_own,
        citation_sources=citation_sources,
    )
