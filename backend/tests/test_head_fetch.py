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
    mock_crawl_settings.return_value.seo_max_chars = 64_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.seo_fallback = False
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
    assert heads["acme.com"].seo == ""
    mock_fetch_page.assert_called_once()
    assert mock_fetch_page.call_args.kwargs["crawl"] is mock_crawl_settings.return_value
    assert mock_fetch_page.call_args.kwargs["max_chars"] == 64_000
    assert mock_fetch_page.call_args.kwargs["crawl_fallback"] is True


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_prefers_website_url(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.seo_max_chars = 64_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.concurrency = 2

    html = "<html><head><title>Tigerobo</title></head></html>"
    mock_fetch_page.return_value = PageFetchResult(
        url="https://www.tigerobo.com/",
        final_url="https://www.tigerobo.com/",
        http_status=200,
        html=html,
        source="httpx",
    )

    heads = fetch_site_heads(
        ["tigerobo.com"],
        preferred_urls={"tigerobo.com": "https://www.tigerobo.com/"},
    )
    assert heads["tigerobo.com"].reachable is True
    mock_fetch_page.assert_called_once_with(
        "https://www.tigerobo.com",
        crawl=mock_crawl_settings.return_value,
        max_chars=64_000,
        crawl_fallback=True,
    )


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_prefers_http_website_url(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.seo_max_chars = 64_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.concurrency = 2

    html = "<html><head><title>中茶</title></head></html>"
    mock_fetch_page.return_value = PageFetchResult(
        url="http://www.chinatea.com.cn/",
        final_url="http://www.chinatea.com.cn/",
        http_status=200,
        html=html,
        source="httpx",
    )

    heads = fetch_site_heads(
        ["chinatea.com.cn"],
        preferred_urls={"chinatea.com.cn": "http://www.chinatea.com.cn/"},
    )
    assert heads["chinatea.com.cn"].reachable is True
    mock_fetch_page.assert_called_once_with(
        "http://www.chinatea.com.cn",
        crawl=mock_crawl_settings.return_value,
        max_chars=64_000,
        crawl_fallback=True,
    )


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_unreachable(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.fetch_timeout_s = 8.0
    mock_crawl_settings.return_value.crawl_timeout_s = 45.0
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.seo_max_chars = 64_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.seo_fallback = False
    mock_crawl_settings.return_value.concurrency = 2

    mock_fetch_page.return_value = PageFetchResult(url="https://bad.com", source="none")

    heads = fetch_site_heads(["bad.com"])
    assert heads["bad.com"].reachable is False


@patch("aperix_geo.services.competitor.head_fetch.fetch_page")
@patch("aperix_geo.services.competitor.head_fetch.page_crawl_settings")
def test_fetch_site_heads_includes_structured_seo(mock_crawl_settings, mock_fetch_page) -> None:
    mock_crawl_settings.return_value.max_chars = 120_000
    mock_crawl_settings.return_value.seo_max_chars = 64_000
    mock_crawl_settings.return_value.crawl_fallback = True
    mock_crawl_settings.return_value.seo_fallback = False
    mock_crawl_settings.return_value.concurrency = 2

    html = """
    <html><head><title>Profound</title><meta name="description" content="GEO analytics" /></head>
    <script type="application/ld+json">
    {
      "@type": "SoftwareApplication",
      "name": "Profound",
      "applicationCategory": "BusinessApplication",
      "brand": {"name": "Profound"}
    }
    </script></html>
    """
    mock_fetch_page.return_value = PageFetchResult(
        url="https://profound.ai",
        final_url="https://profound.ai",
        http_status=200,
        html=html,
        source="httpx",
    )

    heads = fetch_site_heads(["profound.ai"])
    head = heads["profound.ai"]
    assert head.title == "Profound"
    assert "Profound" in head.seo
    assert "schema:" in head.seo
