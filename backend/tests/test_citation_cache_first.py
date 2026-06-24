"""Tests for B2: citation cache-first fetch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.citation.page import CitationPageMeta


@patch("aperix_geo.services.sampling.citation.resolve.fetch_citation_pages_parallel")
@patch("aperix_geo.services.sampling.citation.resolve._load_cached_page_meta")
def test_fetch_citation_pages_cache_first_only_fetches_missing(
    mock_load_cache: MagicMock,
    mock_parallel: MagicMock,
) -> None:
    from aperix_geo.services.sampling.citation.resolve import fetch_citation_pages_for_urls

    job_id = uuid4()
    cached_meta = CitationPageMeta(url="https://cached.com/a", domain="cached.com", fetch_ok=True)
    mock_load_cache.side_effect = [cached_meta, None]
    fetched_meta = CitationPageMeta(url="https://new.com/b", domain="new.com", fetch_ok=True)
    mock_parallel.return_value = [fetched_meta]
    crawl = MagicMock()

    pages = fetch_citation_pages_for_urls(
        ["https://cached.com/a", "https://new.com/b"],
        crawl=crawl,
        snippet_chars=1000,
        sampling_job_id=job_id,
    )

    mock_parallel.assert_called_once()
    assert mock_parallel.call_args.args[0] == ["https://new.com/b"]
    assert len(pages) == 2
    assert pages[0].url == "https://cached.com/a"
    assert pages[1].url == "https://new.com/b"
