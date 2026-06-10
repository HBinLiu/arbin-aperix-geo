"""Tests for job-scoped citation page cache."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.services.sampling.citation.cache.page_meta import (
    clear_job_citation_page_cache,
    get_job_citation_page,
    set_job_citation_page,
)
from aperix_geo.services.sampling.citation.page import CitationPageMeta, fetch_citation_page_meta


def test_job_page_cache_l1_roundtrip() -> None:
    clear_job_citation_page_cache()
    job_id = uuid.uuid4()
    payload = CitationPageMeta(url="https://example.com/a", domain="example.com", fetch_ok=True).to_dict()

    set_job_citation_page(job_id, payload)
    cached = get_job_citation_page(job_id, "https://example.com/a")
    assert cached is not None
    assert cached["url"] == "https://example.com/a"


@patch("aperix_geo.services.sampling.citation.page.fetch_page")
def test_fetch_citation_page_meta_uses_job_cache(mock_fetch: MagicMock) -> None:
    clear_job_citation_page_cache()
    job_id = uuid.uuid4()
    url = "https://example.com/doc"

    fetched = MagicMock()
    fetched.http_status = 200
    fetched.source = "httpx"
    fetched.fetch_ok = True
    fetched.html = "<html><body><h1>Title</h1><p>Body</p></body></html>"
    fetched.markdown = ""
    mock_fetch.return_value = fetched

    first = fetch_citation_page_meta(url, sampling_job_id=job_id)
    second = fetch_citation_page_meta(url, sampling_job_id=job_id)

    assert first.fetch_ok is True
    assert second.fetch_ok is True
    mock_fetch.assert_called_once()
