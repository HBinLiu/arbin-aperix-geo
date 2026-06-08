"""Tests for unified page fetch (httpx + Crawl4AI fallback)."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import httpx
import pytest

from aperix_geo.services.crawl import page_crawl_settings
from aperix_geo.services.crawl._cache import clear_page_cache
from aperix_geo.services.crawl.page import fetch_page


@pytest.fixture(autouse=True)
def _isolate_page_cache_from_redis() -> None:
    with (
        patch(
            "aperix_geo.services.crawl._cache.redis_get_json_with_remaining_ttl",
            return_value=None,
        ),
        patch("aperix_geo.services.crawl._cache.redis_set_json_exat"),
    ):
        yield


class _Response:
    def __init__(self, *, status: int, text: str, url: str) -> None:
        self.status_code = status
        self.text = text
        self.url = url


def test_fetch_page_httpx_success() -> None:
    clear_page_cache()
    html = "<html><head><title>Demo</title></head><body><p>" + ("content " * 20) + "</p></body></html>"
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=0)

    class _Client:
        is_closed = False

        def get(self, url, **kwargs):
            return _Response(status=200, text=html, url=url)

    with patch("aperix_geo.services.crawl.page.get_httpx_client", return_value=_Client()):
        result = fetch_page("https://example.com/page", crawl=crawl)

    assert result.source == "httpx"
    assert result.fetch_ok is True
    assert "Demo" in result.html


def test_fetch_page_falls_back_to_crawl4ai() -> None:
    clear_page_cache()
    crawl = replace(page_crawl_settings(), cache_ttl_s=0)

    class _Client:
        is_closed = False

        def get(self, url, **kwargs):
            raise httpx.HTTPError("blocked")

    with (
        patch("aperix_geo.services.crawl.page.get_httpx_client", return_value=_Client()),
        patch(
            "aperix_geo.services.crawl.page.fetch_url_crawl4ai",
            return_value=("https://example.com/page", "", "## Title\n\nBody " * 10, "crawl4ai"),
        ),
    ):
        result = fetch_page("https://example.com/page", crawl=crawl)

    assert result.source == "crawl4ai"
    assert result.fetch_ok is True
    assert "Title" in result.markdown
