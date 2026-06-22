"""Tests for global URL citation page metadata cache."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.sampling.citation.cache.url_meta import (
    clear_url_citation_page_cache,
    get_url_citation_page,
    set_url_citation_page,
)
from aperix_geo.services.sampling.citation.page import CitationPageMeta


def test_url_meta_cache_roundtrip() -> None:
    clear_url_citation_page_cache()
    payload = CitationPageMeta(
        url="https://wise.com/a",
        domain="wise.com",
        fetch_ok=True,
        title="Title",
    ).to_dict()

    set_url_citation_page(payload)
    cached = get_url_citation_page("https://wise.com/a")
    assert cached is not None
    assert cached["title"] == "Title"


@patch("aperix_geo.services.sampling.citation.cache.url_meta._url_meta_cache_ttl_s", return_value=0)
def test_url_meta_cache_disabled_when_ttl_zero(_mock_ttl) -> None:
    clear_url_citation_page_cache()
    payload = CitationPageMeta(url="https://wise.com/a", domain="wise.com", fetch_ok=True).to_dict()

    set_url_citation_page(payload)
    assert get_url_citation_page("https://wise.com/a") is None
