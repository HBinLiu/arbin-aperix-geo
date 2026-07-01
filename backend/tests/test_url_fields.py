"""Tests for url_fields validation."""

import pytest
from pydantic import ValidationError

from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.schemas.url_fields import validate_optional_http_url
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url


def test_validate_optional_http_url_bare_domain() -> None:
    assert validate_optional_http_url("geo.example.com") == "geo.example.com"
    assert validate_optional_http_url("geo.example.com/about") == "geo.example.com/about"


def test_validate_optional_http_url_with_scheme() -> None:
    assert validate_optional_http_url("http://example.com") == "http://example.com"
    assert validate_optional_http_url("https://geo.example.com/path") == "https://geo.example.com/path"


def test_validate_optional_http_url_empty() -> None:
    assert validate_optional_http_url("") == ""
    assert validate_optional_http_url(None) == ""


def test_validate_optional_http_url_invalid() -> None:
    with pytest.raises(ValueError):
        validate_optional_http_url("not-a-url")


def test_prepare_domain_preserves_bare_website_url() -> None:
    domain, url = prepare_domain_and_website_url("example.com", "geo.example.com", probe=False)
    assert domain == "example.com"
    assert url == "geo.example.com"


def test_competitor_item_accepts_bare_website_url() -> None:
    item = CompetitorItem(domain="wise.com", brand="Wise", website_url="geo.wise.com/path")
    assert item.website_url == "geo.wise.com/path"

    with pytest.raises(ValidationError):
        CompetitorItem(domain="wise.com", brand="Wise", website_url="not-a-url")
