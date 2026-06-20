"""Tests for competitor homepage context fetching."""

from unittest.mock import patch

from aperix_geo.services.competitor.web_context import fetch_site_homepage_context
from aperix_geo.services.crawl.types import PageFetchResult


@patch("aperix_geo.services.competitor.web_context.fetch_page")
@patch("aperix_geo.services.competitor.web_context.host_resolves", return_value=True)
def test_fetch_site_homepage_tries_user_url_before_apex(mock_resolve, mock_fetch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str, **kwargs) -> PageFetchResult:
        calls.append(url)
        if url == "https://www.sheepgeo.com/about":
            html = (
                "<html><head><title>About</title></head>"
                "<body>" + ("content " * 20) + "</body></html>"
            )
            return PageFetchResult(
                url=url,
                final_url=url,
                http_status=200,
                html=html,
                source="httpx",
            )
        return PageFetchResult(url=url, source="none")

    mock_fetch.side_effect = fake_fetch
    ctx = fetch_site_homepage_context(
        "sheepgeo.com",
        user_url="https://www.sheepgeo.com/about",
    )
    assert ctx.url == "https://www.sheepgeo.com/about"
    assert calls[0] == "https://www.sheepgeo.com/about"


@patch("aperix_geo.services.competitor.web_context.fetch_page")
@patch("aperix_geo.services.competitor.web_context.host_resolves", return_value=True)
def test_fetch_site_homepage_falls_back_to_apex(mock_resolve, mock_fetch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str, **kwargs) -> PageFetchResult:
        calls.append(url)
        if "www." in url:
            return PageFetchResult(url=url, source="none")
        html = (
            "<html><head><title>SheepGeo</title></head>"
            "<body>" + ("content " * 20) + "</body></html>"
        )
        return PageFetchResult(
            url=url,
            final_url=url,
            http_status=200,
            html=html,
            source="httpx",
        )

    mock_fetch.side_effect = fake_fetch
    ctx = fetch_site_homepage_context("sheepgeo.com", user_url="sheepgeo.com")
    assert ctx.url.rstrip("/") == "https://sheepgeo.com"
    assert calls[0] == "https://sheepgeo.com"
    assert all("www." not in u for u in calls[:2])
