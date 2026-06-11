"""Citation URL resolution: page fetch, GEO analysis, source metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.citation.document import CitationDocument
from aperix_geo.services.sampling.citation.labels import brand_names_match, page_mentioned_brand_names
from aperix_geo.services.sampling.citation.page import fetch_citation_pages_parallel
from aperix_geo.services.sampling.citation.page_geo import (
    analyze_citation_pages_geo,
    heuristic_page_mentioned_brands,
)
from aperix_geo.services.sampling.mentions import CompetitorEntry, collect_match_terms
from aperix_geo.utils.url import host_matches_root, hostname_from_url, normalize_domain

if TYPE_CHECKING:
    from aperix_geo.services.crawl.settings import PageCrawlSettings


def citation_root(subject: Subject) -> str | None:
    if subject.website_url:
        root = normalize_domain(hostname_from_url(subject.website_url))
        if root:
            return root
    if subject.type == SubjectType.domain and subject.domain:
        return normalize_domain(subject.domain)
    return None


def _url_matches_competitor(url: str, entry: CompetitorEntry) -> bool:
    if not entry.domain:
        return False
    root = normalize_domain(entry.domain) or entry.domain.lower()
    return host_matches_root(hostname_from_url(url), root)


def _url_target(url: str, *, root: str | None, competitors: list[CompetitorEntry]) -> str:
    if root and host_matches_root(hostname_from_url(url), root):
        return "own"
    for entry in competitors:
        if _url_matches_competitor(url, entry):
            return entry.label
    return ""


def resolve_citation_sources(
    urls: list[str],
    *,
    root: str | None,
    own_names: list[str],
    own_brand: str,
    competitors: list[CompetitorEntry],
    crawl: PageCrawlSettings,
    snippet_chars: int,
    llm_enabled: bool,
    geo_cache_ttl_s: int,
    geo_batch_size: int,
    sampling_job_id: UUID | None = None,
) -> CitationDocument:
    """并行抓取来源页；批量 Page GEO / 来源页提及分析。"""
    competitor_brand_names = [entry.brand or entry.label for entry in competitors if entry.brand or entry.label]
    own_brand_keys = collect_match_terms(own_brand, *own_names)

    citation_urls_own = [url for url in urls if root and host_matches_root(hostname_from_url(url), root)]
    citation_sources: list[dict] = []

    pages = fetch_citation_pages_parallel(
        urls,
        crawl=crawl,
        snippet_chars=snippet_chars,
        sampling_job_id=sampling_job_id,
    )

    if llm_enabled:
        page_analyses = analyze_citation_pages_geo(
            pages,
            own_brand=own_brand,
            competitors=competitor_brand_names,
            cache_ttl_s=geo_cache_ttl_s,
            batch_size=geo_batch_size,
        )
    else:
        page_analyses = []
        for page in pages:
            if page.fetch_ok:
                page_analyses.append(
                    {
                        "page_mentioned_brands": heuristic_page_mentioned_brands(
                            page,
                            own_brand=own_brand,
                            competitors=competitor_brand_names,
                            own_aliases=own_names,
                        ),
                        "domain_classification": {"type": "", "reason": ""},
                        "url_classification": {"type": "", "reason": ""},
                        "analysis_source": "heuristic",
                    },
                )
            else:
                page_analyses.append({})

    for page, page_analysis in zip(pages, page_analyses):
        target = _url_target(page.url, root=root, competitors=competitors)
        page_mentioned = page_mentioned_brand_names(page_analysis)

        domain_cls = (
            page_analysis.get("domain_classification")
            if isinstance(page_analysis.get("domain_classification"), dict)
            else {}
        )
        url_cls = (
            page_analysis.get("url_classification")
            if isinstance(page_analysis.get("url_classification"), dict)
            else {}
        )

        citation_sources.append(
            {
                "url": page.url,
                "domain": page.domain,
                "http_status": page.http_status,
                "page_title": page.title,
                "description": page.description,
                "headings": page.headings,
                "has_table": page.has_table,
                "has_code_block": page.has_code_block,
                "text_snippet": page.text_snippet,
                "fetch_ok": page.fetch_ok,
                "target": target,
                "page_mentions_brand": target == "own" and brand_names_match(own_brand_keys, page_mentioned),
                "domain_type": str(domain_cls.get("type") or domain_cls.get("detected_domain_type") or "").strip(),
                "url_type": str(url_cls.get("type") or url_cls.get("detected_type") or "").strip(),
                "llm_analysis": page_analysis,
            }
        )

    return CitationDocument(
        citation_urls_own=citation_urls_own,
        citation_sources=citation_sources,
    )
