"""Tests for URL helpers."""

from aperix_geo.utils.url import (
    extract_urls,
    host_matches_root,
    hostname_from_url,
    normalize_domain,
)


def test_extract_urls_dedupes() -> None:
    text = "See https://a.com/x and https://a.com/x and https://b.com"
    assert extract_urls(text) == ["https://a.com/x", "https://b.com"]


def test_hostname_from_url_strips_port_and_www() -> None:
    assert hostname_from_url("https://www.Example.com:443/path") == "example.com"


def test_normalize_domain() -> None:
    assert normalize_domain("WWW.Example.COM") == "example.com"
    assert normalize_domain(None) is None


def test_host_matches_root() -> None:
    assert host_matches_root("www.blog.example.com", "example.com")
    assert not host_matches_root("other.com", "example.com")
