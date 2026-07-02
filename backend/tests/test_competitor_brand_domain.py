"""Tests for brand-mode competitor domain reconciliation."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.brand_domain import (
    reconcile_brand_competitor_domain,
    reconcile_brand_competitor_domains,
)
from aperix_geo.services.competitor.types import SiteHead


@patch("aperix_geo.services.competitor.brand_domain.fetch_site_heads")
@patch("aperix_geo.services.competitor.brand_domain.search_brand_official_domain")
@patch("aperix_geo.services.competitor.brand_domain.accept_discovered_domain", return_value=True)
def test_prefers_doubao_url_when_verified(mock_accept, mock_search, mock_fetch) -> None:
    mock_fetch.return_value = {
        "dayitea.com": SiteHead(
            "dayitea.com",
            "大益茶业官网",
            "",
            True,
            resolved_url="https://www.dayitea.com/",
        ),
    }
    item = {
        "brand": "大益茶业",
        "domain": "dayitea.com",
        "website_url": "https://www.dayitea.com/",
    }
    out, head = reconcile_brand_competitor_domain(item)
    assert out["domain"] == "dayitea.com"
    assert "dayitea.com" in out["website_url"]
    assert head is not None
    mock_accept.assert_called_once_with(
        "dayitea.com",
        "大益茶业",
        preferred_url="https://www.dayitea.com",
    )
    mock_search.assert_not_called()


@patch("aperix_geo.services.competitor.brand_domain.fetch_site_heads")
@patch("aperix_geo.services.competitor.brand_domain.search_brand_official_domain")
@patch("aperix_geo.services.competitor.brand_domain.accept_discovered_domain")
def test_falls_back_to_searxng_when_doubao_rejected(mock_accept, mock_search, mock_fetch) -> None:
    mock_accept.side_effect = lambda domain, _brand, **kwargs: domain == "dayitea.com"
    mock_search.return_value = "dayitea.com"
    mock_fetch.return_value = {
        "dayitea.com": SiteHead(
            "dayitea.com",
            "大益茶业官网",
            "",
            True,
            resolved_url="https://www.dayitea.com/",
        ),
    }
    item = {
        "brand": "大益茶业",
        "domain": "fake.com",
        "website_url": "https://fake.com",
    }
    out, head = reconcile_brand_competitor_domain(item)
    assert out["domain"] == "dayitea.com"
    assert head is not None
    mock_accept.assert_any_call("fake.com", "大益茶业", preferred_url="https://fake.com")
    mock_search.assert_called_once_with("大益茶业")


@patch("aperix_geo.services.competitor.brand_domain.fetch_site_heads")
@patch("aperix_geo.services.competitor.brand_domain.search_brand_official_domain")
def test_resolves_domain_via_searxng(mock_search, mock_fetch) -> None:
    mock_search.return_value = "dayitea.com"
    mock_fetch.return_value = {
        "dayitea.com": SiteHead(
            "dayitea.com",
            "大益茶业官网",
            "",
            True,
            resolved_url="https://www.dayitea.com/",
        ),
    }
    item = {"brand": "大益茶业", "domain": "", "website_url": ""}
    out, head = reconcile_brand_competitor_domain(item)
    assert out["domain"] == "dayitea.com"
    assert "dayitea.com" in out["website_url"]
    assert head is not None
    mock_search.assert_called_once_with("大益茶业")


@patch("aperix_geo.services.competitor.brand_domain.search_brand_official_domain")
@patch("aperix_geo.services.competitor.brand_domain.accept_discovered_domain", return_value=False)
def test_strips_domain_when_all_sources_miss(mock_accept, mock_search) -> None:
    mock_search.return_value = ""
    item = {"brand": "某茶品牌", "domain": "bad.com", "website_url": "https://bad.com"}
    out, head = reconcile_brand_competitor_domain(item)
    assert out["domain"] == ""
    assert out["website_url"] == ""
    assert out["brand"] == "某茶品牌"
    assert head is None


@patch("aperix_geo.services.competitor.brand_domain.fetch_site_heads")
@patch("aperix_geo.services.competitor.brand_domain.search_brand_official_domain")
@patch("aperix_geo.services.competitor.brand_domain.accept_discovered_domain", return_value=True)
def test_reconcile_batch_collects_heads(mock_accept, mock_search, mock_fetch) -> None:
    mock_fetch.return_value = {
        "a.com": SiteHead("a.com", "A", "", True, resolved_url="https://a.com"),
    }
    items = [{"brand": "A", "domain": "a.com", "website_url": "https://a.com"}]
    resolved, heads = reconcile_brand_competitor_domains(items)
    assert resolved[0]["domain"] == "a.com"
    assert heads["a.com"].domain == "a.com"
    mock_fetch.assert_called_once_with(
        ["a.com"],
        preferred_urls={"a.com": "https://a.com"},
    )
    mock_search.assert_not_called()
