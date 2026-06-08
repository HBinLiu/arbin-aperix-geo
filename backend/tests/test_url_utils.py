"""Tests for URL helpers."""

from aperix_geo.utils.url import (
    extract_urls,
    filter_citation_urls,
    host_matches_root,
    hostname_from_url,
    is_placeholder_citation_host,
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


def test_is_placeholder_citation_host() -> None:
    assert is_placeholder_citation_host("example.com")
    assert is_placeholder_citation_host("blog.example.com")
    assert is_placeholder_citation_host("www.example.org")
    assert is_placeholder_citation_host("localhost")
    assert not is_placeholder_citation_host("wise.com")
    assert not is_placeholder_citation_host("11467.com")


def test_filter_citation_urls() -> None:
    urls = filter_citation_urls(
        [
            "https://example.com/a",
            "https://wise.com/b",
            "https://wise.com/b",
        ]
    )
    assert urls == ["https://wise.com/b"]
