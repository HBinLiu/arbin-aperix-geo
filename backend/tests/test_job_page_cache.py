"""Tests for job-scoped citation page cache."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.services.sampling.citation.cache.page_meta import (
    clear_job_citation_page_cache,
    get_job_citation_page,
    set_job_citation_page,
)
from aperix_geo.services.sampling.citation.cache.url_meta import clear_url_citation_page_cache
from aperix_geo.services.sampling.citation.page import CitationPageMeta, fetch_citation_page_meta


def test_job_page_cache_l1_roundtrip() -> None:
    clear_job_citation_page_cache()
    job_id = uuid.uuid4()
    payload = CitationPageMeta(url="https://wise.com/a", domain="wise.com", fetch_ok=True).to_dict()

    set_job_citation_page(job_id, payload)
    cached = get_job_citation_page(job_id, "https://wise.com/a")
    assert cached is not None
    assert cached["url"] == "https://wise.com/a"


def test_job_page_cache_disabled_when_ttl_zero() -> None:
    clear_job_citation_page_cache()
    job_id = uuid.uuid4()
    payload = CitationPageMeta(url="https://wise.com/a", domain="wise.com", fetch_ok=True).to_dict()

    with patch(
        "aperix_geo.services.sampling.citation.cache.page_meta._job_page_cache_ttl_s",
        return_value=0,
    ):
        set_job_citation_page(job_id, payload)
        assert get_job_citation_page(job_id, "https://wise.com/a") is None


@patch("aperix_geo.services.sampling.citation.cache.url_meta.get_url_citation_page", return_value=None)
@patch("aperix_geo.services.sampling.citation.page.fetch_page")
def test_fetch_citation_page_meta_uses_job_cache(mock_fetch: MagicMock, _mock_url_cache: MagicMock) -> None:
    clear_job_citation_page_cache()
    clear_url_citation_page_cache()
    job_id = uuid.uuid4()
    url = "https://wise.com/doc"

    fetched = MagicMock()
    fetched.http_status = 200
    fetched.source = "httpx"
    fetched.fetch_ok = True
    fetched.final_url = url
    fetched.html = "<html><body><h1>Title</h1><p>Body</p></body></html>"
    fetched.markdown = ""
    mock_fetch.return_value = fetched

    first = fetch_citation_page_meta(url, sampling_job_id=job_id)
    second = fetch_citation_page_meta(url, sampling_job_id=job_id)

    assert first.fetch_ok is True
    assert second.fetch_ok is True
    mock_fetch.assert_called_once()
