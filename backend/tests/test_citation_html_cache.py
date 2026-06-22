"""Tests for citation page HTML cache fast path."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock, patch

from aperix_geo.services.crawl import page_crawl_settings
from aperix_geo.services.crawl._cache import clear_page_cache, set_cached_page
from aperix_geo.services.crawl.types import PageFetchResult
from aperix_geo.services.sampling.citation.cache.page_meta import clear_job_citation_page_cache
from aperix_geo.services.sampling.citation.cache.url_meta import (
    clear_url_citation_page_cache,
    get_url_citation_page,
)
from aperix_geo.services.sampling.citation.page import fetch_citation_page_meta


def _sample_html(title: str = "Cached Title") -> str:
    return (
        f"<html><head><title>{title}</title>"
        f"<meta name='description' content='Cached description'></head>"
        f"<body><p>{'content ' * 30}</p></body></html>"
    )


@patch("aperix_geo.services.sampling.citation.page.fetch_page")
def test_fetch_citation_page_meta_builds_from_html_cache_without_fetch(mock_fetch: MagicMock) -> None:
    clear_page_cache()
    clear_job_citation_page_cache()
    clear_url_citation_page_cache()

    url = "https://wise.com/cached-doc-a"
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=86_400)
    html = _sample_html()
    set_cached_page(
        url,
        PageFetchResult(
            url=url,
            final_url=url,
            http_status=200,
            html=html,
            source="httpx",
        ),
        max_chars=crawl.max_chars,
        crawl_fallback=crawl.crawl_fallback,
        ttl_s=crawl.cache_ttl_s,
    )

    meta = fetch_citation_page_meta(url, crawl=crawl)

    mock_fetch.assert_not_called()
    assert meta.fetch_ok is True
    assert meta.title == "Cached Title"
    assert get_url_citation_page(url) is not None


@patch("aperix_geo.services.sampling.citation.page.fetch_page")
def test_fetch_citation_page_meta_html_cache_matches_utm_variant(mock_fetch: MagicMock) -> None:
    clear_page_cache()
    clear_url_citation_page_cache()

    url = "https://wise.com/cached-doc-b"
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=86_400)
    set_cached_page(
        url,
        PageFetchResult(
            url=url,
            final_url=url,
            http_status=200,
            html=_sample_html("Norm"),
            source="httpx",
        ),
        max_chars=crawl.max_chars,
        crawl_fallback=crawl.crawl_fallback,
        ttl_s=crawl.cache_ttl_s,
    )

    meta = fetch_citation_page_meta("https://wise.com/cached-doc-b?utm=1", crawl=crawl)

    mock_fetch.assert_not_called()
    assert meta.title == "Norm"
    assert get_url_citation_page("https://wise.com/cached-doc-b?utm=tracker") is not None
