"""Tests for per-domain page crawl limits."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.services.crawl import page_crawl_settings
from aperix_geo.services.crawl._cache import clear_page_cache
from aperix_geo.services.crawl.limits import (
    CrawlRateLimitError,
    normalize_crawl_domain,
    page_crawl_slot,
)
from aperix_geo.services.crawl.page import fetch_page


def test_normalize_crawl_domain_from_url() -> None:
    assert normalize_crawl_domain("https://News.Wise.com/path") == "wise.com"
    assert normalize_crawl_domain("blog.example.co.uk") == "example.co.uk"


@patch("aperix_geo.services.crawl.limits.get_settings")
@patch("aperix_geo.services.crawl.limits.shared_redis_client")
def test_page_crawl_slot_acquires_and_releases_inflight(mock_client: MagicMock, mock_settings: MagicMock) -> None:
    settings = MagicMock()
    settings.page_crawl_domain_limit_per_minute = 30
    settings.page_crawl_domain_max_inflight = 3
    settings.page_crawl_domain_limit_wait_s = 15.0
    settings.page_crawl_domain_inflight_ttl_s = 600
    mock_settings.return_value = settings

    redis = MagicMock()
    redis.incr.side_effect = [1, 1]
    redis.ttl.return_value = 600
    redis.decr.return_value = 0
    mock_client.return_value = redis

    with page_crawl_slot("https://wise.com/page") as domain:
        assert domain == "wise.com"

    assert redis.incr.call_count == 2
    redis.decr.assert_called_once()
    redis.delete.assert_called_once()


@patch("aperix_geo.services.crawl.limits.get_settings")
@patch("aperix_geo.services.crawl.limits.shared_redis_client")
def test_page_crawl_slot_raises_when_minute_quota_exceeded(mock_client: MagicMock, mock_settings: MagicMock) -> None:
    settings = MagicMock()
    settings.page_crawl_domain_limit_per_minute = 2
    settings.page_crawl_domain_max_inflight = 0
    settings.page_crawl_domain_limit_wait_s = 0.0
    settings.page_crawl_domain_inflight_ttl_s = 600
    mock_settings.return_value = settings

    redis = MagicMock()
    redis.incr.return_value = 3
    mock_client.return_value = redis

    with pytest.raises(CrawlRateLimitError, match="rate limit exceeded"):
        with page_crawl_slot("wise.com"):
            pass

    redis.decr.assert_called_once()


@patch("aperix_geo.services.crawl.page.set_negative_cached_page")
@patch("aperix_geo.services.crawl.page.page_crawl_slot")
def test_fetch_page_stores_soft_negative_on_rate_limit(
    mock_slot: MagicMock,
    mock_negative: MagicMock,
) -> None:
    clear_page_cache()
    crawl = replace(
        page_crawl_settings(),
        crawl_fallback=False,
        cache_ttl_s=3600,
        negative_cache_ttl_s=300,
        rate_limit_negative_ttl_s=60,
    )
    mock_slot.side_effect = CrawlRateLimitError("limited")

    with (
        patch("aperix_geo.services.crawl.page.host_resolves", return_value=True),
        patch("aperix_geo.services.crawl.page.host_resolves_public", return_value=True),
        patch("aperix_geo.services.crawl.page.get_httpx_client") as mock_client,
    ):
        result = fetch_page("https://wise.com/rate-limited", crawl=crawl)

    assert result.source == "none"
    assert not result.fetch_ok
    mock_client.assert_not_called()
    mock_negative.assert_called_once()
    _, kwargs = mock_negative.call_args
    assert kwargs["negative_ttl_s"] == 60


@patch("aperix_geo.services.crawl.page.set_negative_cached_page")
@patch("aperix_geo.services.crawl.page.page_crawl_slot")
def test_fetch_page_skips_soft_negative_when_rate_limit_ttl_zero(
    mock_slot: MagicMock,
    mock_negative: MagicMock,
) -> None:
    clear_page_cache()
    crawl = replace(
        page_crawl_settings(),
        crawl_fallback=False,
        cache_ttl_s=3600,
        negative_cache_ttl_s=300,
        rate_limit_negative_ttl_s=0,
    )
    mock_slot.side_effect = CrawlRateLimitError("limited")

    with (
        patch("aperix_geo.services.crawl.page.host_resolves", return_value=True),
        patch("aperix_geo.services.crawl.page.host_resolves_public", return_value=True),
        patch("aperix_geo.services.crawl.page.get_httpx_client"),
    ):
        result = fetch_page("https://wise.com/rate-limited", crawl=crawl)

    assert result.source == "none"
    mock_negative.assert_not_called()
