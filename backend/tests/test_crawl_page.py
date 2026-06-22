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
        patch("aperix_geo.services.crawl.page.host_resolves", return_value=True),
        patch("aperix_geo.services.crawl.page.host_resolves_to_public_addresses", return_value=True),
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
        result = fetch_page("https://wise.com/page", crawl=crawl)

    assert result.source == "httpx"
    assert result.fetch_ok is True
    assert "Demo" in result.html


def test_fetch_page_skips_invalid_citation_url() -> None:
    clear_page_cache()
    crawl = replace(page_crawl_settings(), crawl_fallback=True, cache_ttl_s=0)

    with patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client:
        with patch("aperix_geo.services.crawl.page.fetch_url_crawl4ai") as mock_crawl:
            result = fetch_page("https://0.5/", crawl=crawl)

    assert result.source == "none"
    assert not result.fetch_ok
    mock_client.assert_not_called()
    mock_crawl.assert_not_called()


def test_fetch_page_skips_single_label_host() -> None:
    clear_page_cache()
    crawl = replace(page_crawl_settings(), crawl_fallback=True, cache_ttl_s=0)

    with patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client:
        with patch("aperix_geo.services.crawl.page.fetch_url_crawl4ai") as mock_crawl:
            result = fetch_page("https://jiqiz/", crawl=crawl)

    assert result.source == "none"
    assert not result.fetch_ok
    mock_client.assert_not_called()
    mock_crawl.assert_not_called()


def test_fetch_page_skips_private_resolved_host() -> None:
    clear_page_cache()
    crawl = replace(page_crawl_settings(), crawl_fallback=True, cache_ttl_s=0)

    with (
        patch("aperix_geo.services.crawl.page.host_resolves", return_value=True),
        patch("aperix_geo.services.crawl.page.host_resolves_to_public_addresses", return_value=False),
        patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client,
        patch("aperix_geo.services.crawl.page.fetch_url_crawl4ai") as mock_crawl,
    ):
        result = fetch_page("https://wise.com/internal", crawl=crawl)

    assert result.source == "none"
    mock_client.assert_not_called()
    mock_crawl.assert_not_called()


def test_fetch_page_skips_unresolvable_host() -> None:
    clear_page_cache()
    crawl = replace(page_crawl_settings(), crawl_fallback=True, cache_ttl_s=0)

    with (
        patch("aperix_geo.services.crawl.page.host_resolves", return_value=False),
        patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client,
        patch("aperix_geo.services.crawl.page.fetch_url_crawl4ai") as mock_crawl,
    ):
        result = fetch_page("https://wise.com/page", crawl=crawl)

    assert result.source == "none"
    assert not result.fetch_ok
    mock_client.assert_not_called()
    mock_crawl.assert_not_called()


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
            return_value=("https://wise.com/page", "", "## Title\n\nBody " * 10, "crawl4ai"),
        ),
    ):
        result = fetch_page("https://wise.com/page", crawl=crawl)

    assert result.source == "crawl4ai"
    assert result.fetch_ok is True
    assert "Title" in result.markdown


def test_fetch_page_cache_hit() -> None:
    clear_page_cache()
    html = "<html><head><title>Cached</title></head><body><p>" + ("x " * 30) + "</p></body></html>"
    calls = {"n": 0}
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=3600)

    class _Client:
        def get(self, url, **kwargs):
            calls["n"] += 1
            return _Response(status=200, text=html, url=url)

    with patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client:
        mock_client.return_value = _Client()
        first = fetch_page("https://wise.com/a", crawl=crawl)
        second = fetch_page("https://wise.com/a", crawl=crawl)

    assert first.fetch_ok is True
    assert second.source == first.source
    assert calls["n"] == 1


def test_fetch_page_cache_disabled() -> None:
    clear_page_cache()
    html = "<html><head><title>Fresh</title></head><body><p>" + ("y " * 30) + "</p></body></html>"
    calls = {"n": 0}
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=0)

    class _Client:
        def get(self, url, **kwargs):
            calls["n"] += 1
            return _Response(status=200, text=html, url=url)

    with patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client:
        mock_client.return_value = _Client()
        fetch_page("https://wise.com/b", crawl=crawl)
        fetch_page("https://wise.com/b", crawl=crawl)

    assert calls["n"] == 2


def test_fetch_page_negative_cache() -> None:
    clear_page_cache()
    httpx_calls = {"n": 0}
    crawl_calls = {"n": 0}
    crawl = replace(
        page_crawl_settings(),
        cache_ttl_s=3600,
        negative_cache_ttl_s=300,
    )

    class _Client:
        def get(self, url, **kwargs):
            httpx_calls["n"] += 1
            raise httpx.HTTPError("down")

    def _crawl4ai(url, **kwargs):
        crawl_calls["n"] += 1
        return url, "", "", "none"

    with (
        patch("aperix_geo.services.crawl.page.get_httpx_client", return_value=_Client()),
        patch("aperix_geo.services.crawl.page.fetch_url_crawl4ai", side_effect=_crawl4ai),
    ):
        fetch_page("https://wise.com/dead", crawl=crawl)
        fetch_page("https://wise.com/dead", crawl=crawl)

    assert httpx_calls["n"] == 1
    assert crawl_calls["n"] == 1


def test_fetch_page_cache_normalizes_url() -> None:
    clear_page_cache()
    html = "<html><head><title>Norm</title></head><body><p>" + ("z " * 30) + "</p></body></html>"
    calls = {"n": 0}
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=3600)

    class _Client:
        def get(self, url, **kwargs):
            calls["n"] += 1
            return _Response(status=200, text=html, url=url)

    with patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client:
        mock_client.return_value = _Client()
        fetch_page("https://wise.com/page/?utm_source=newsletter", crawl=crawl)
        fetch_page("https://Wise.com/page", crawl=crawl)

    assert calls["n"] == 1


def test_page_cache_memory_backfill_uses_remaining_ttl() -> None:
    import time

    from aperix_geo.services.crawl._cache import get_cached_page, set_cached_page
    from aperix_geo.services.crawl.types import PageFetchResult

    clear_page_cache()
    html = "<html><head><title>T</title></head><body><p>" + ("a " * 30) + "</p></body></html>"
    result = PageFetchResult(
        url="https://wise.com/t",
        final_url="https://wise.com/t",
        http_status=200,
        html=html,
        source="httpx",
    )
    expires_at = int(time.time()) + 30
    crawl = replace(page_crawl_settings(), crawl_fallback=False, cache_ttl_s=3600)
    with patch("aperix_geo.services.crawl._cache.redis_set_json_exat") as mock_set:
        with patch(
            "aperix_geo.services.crawl._cache.redis_get_json_with_remaining_ttl",
            return_value=({"url": result.url, "final_url": result.final_url, "http_status": 200, "html": html, "markdown": "", "source": "httpx", "expires_at": expires_at}, 12),
        ):
            set_cached_page(
                "https://wise.com/t",
                result,
                max_chars=crawl.max_chars,
                crawl_fallback=crawl.crawl_fallback,
                ttl_s=crawl.cache_ttl_s,
            )
            clear_page_cache()
            hit = get_cached_page(
                "https://wise.com/t",
                max_chars=crawl.max_chars,
                crawl_fallback=crawl.crawl_fallback,
                ttl_s=crawl.cache_ttl_s,
            )
    assert hit is not None
    assert hit.fetch_ok is True
    mock_set.assert_called_once()
