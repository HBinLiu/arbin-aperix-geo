"""Tests for competitor head fetch via unified crawl."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.crawl.types import PageFetchResult


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_uses_unified_crawl(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.fetch_timeout_s = 8.0
    mock_crawl_settings.return_value.crawl_timeout_s = 45.0
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.concurrency = 2

    html = "<html><head><title>Acme Pay</title><meta name='description' content='跨境支付'></head></html>"
    mock_fetch_page.return_value = PageFetchResult(
        url="https://acme.com",
        final_url="https://acme.com",
        http_status=200,
        html=html,
        source="httpx",
    )

    heads = fetch_site_heads(["acme.com"])
    assert heads["acme.com"].reachable is True
    assert heads["acme.com"].title == "Acme Pay"
    assert heads["acme.com"].description == "跨境支付"
    mock_fetch_page.assert_called_once()
    assert mock_fetch_page.call_args.kwargs["crawl"] is mock_crawl_settings.return_value
    assert mock_fetch_page.call_args.kwargs["max_chars"] == 80_000


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_unreachable(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.fetch_timeout_s = 8.0
    mock_crawl_settings.return_value.crawl_timeout_s = 45.0
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.concurrency = 2

    mock_fetch_page.return_value = PageFetchResult(url="https://bad.com", source="none")

    heads = fetch_site_heads(["bad.com"])
    assert heads["bad.com"].reachable is False
