"""Tests for URL resolution and normalization helpers."""

from unittest.mock import MagicMock, patch

import httpx

from aperix_geo.services.crawl._crawl4ai import result_markdown
from aperix_geo.utils.url import (
    fallback_website_url,
    homepage_urls,
    homepage_urls_apex_first,
    host_resolves,
    normalize_crawl_cache_url,
    normalize_page_url,
    profile_homepage_crawl_urls,
    resolve_website_url,
    root_website_url,
)


def test_root_website_url() -> None:
    assert root_website_url("https://www.Example.com/path?q=1") == "https://www.example.com"


def test_prepare_domain_and_website_url_preserves_user_input() -> None:
    from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url

    domain, url = prepare_domain_and_website_url("aibase.com", "https://geo.aibase.com/")
    assert domain == "aibase.com"
    assert url == "https://geo.aibase.com/"

    domain, url = prepare_domain_and_website_url(
        "aibase.com",
        "https://geo.aibase.com/about",
        probe=False,
    )
    assert domain == "aibase.com"
    assert url == "https://geo.aibase.com/about"


def test_resolve_website_url_without_probe() -> None:
    domain, url = resolve_website_url("https://www.stripe.com/pricing", probe=False)
    assert domain == "stripe.com"
    assert url == fallback_website_url("stripe.com")


@patch("aperix_geo.utils.url.host_resolves", return_value=False)
def test_resolve_website_url_probe_success(_mock_resolve: MagicMock) -> None:
    class _Client:
        def get(self, url: str, **kwargs):  # noqa: ANN003
            if url == "https://example.com":
                return httpx.Response(200, request=httpx.Request("GET", url))
            raise httpx.HTTPError("unreachable")

        def __enter__(self):
            return self

        def __exit__(self, *args):  # noqa: ANN002
            return False

    with patch("aperix_geo.utils.url.httpx.Client", return_value=_Client()):
        domain, url = resolve_website_url("example.com", probe=True, timeout_s=1.0)

    assert domain == "example.com"
    assert url == "https://example.com"


def test_normalize_page_url() -> None:
    assert normalize_page_url("https://Example.com/about/") == "https://example.com/about"
    assert normalize_page_url("https://example.com/pricing#x") == "https://example.com/pricing"


def test_normalize_crawl_cache_url() -> None:
    assert normalize_crawl_cache_url("https://Example.com/page/?utm_source=x&a=1") == (
        "https://example.com/page?a=1"
    )
    assert normalize_crawl_cache_url("https://example.com/page/?fbclid=abc") == "https://example.com/page"


def test_result_markdown_from_object() -> None:
    class _Md:
        fit_markdown = "## About\n\nPayments."

    class _R:
        markdown = _Md()

    assert "Payments" in result_markdown(_R())


def test_host_resolves_invalid() -> None:
    assert not host_resolves("this-domain-definitely-does-not-exist-aperix.test")


def test_homepage_urls_prefers_www(monkeypatch) -> None:
    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"shushangyun.com", "www.shushangyun.com"},
    )
    urls = homepage_urls("shushangyun.com")
    assert urls[0] == "https://www.shushangyun.com/"
    assert urls[1] == "https://shushangyun.com/"
    assert all(u.startswith("https://") for u in urls)


def test_homepage_urls_apex_first(monkeypatch) -> None:
    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"example.com", "www.example.com"},
    )
    urls = homepage_urls_apex_first("example.com")
    assert urls[0] == "https://example.com/"
    assert urls[1] == "https://www.example.com/"


def test_profile_homepage_crawl_urls_user_input_first() -> None:
    urls = profile_homepage_crawl_urls(
        "https://www.sheepgeo.com/about",
        root="sheepgeo.com",
    )
    assert urls[0] == "https://www.sheepgeo.com/about"
    assert "https://sheepgeo.com/" in urls
