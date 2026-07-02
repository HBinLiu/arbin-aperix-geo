"""Tests for URL resolution and normalization helpers."""

from unittest.mock import MagicMock, patch

import httpx

from aperix_geo.services.crawl._crawl4ai import result_markdown
from aperix_geo.utils.url import (
    apex_homepage_urls,
    crawl_cache_url,
    homepage_urls,
    host_resolves,
    page_url,
    profile_crawl_urls,
    resolve_website,
    website_fallback,
    website_root_url,
)


def test_website_root_url() -> None:
    assert website_root_url("https://www.Example.com/path?q=1") == "https://www.example.com"


def test_prepare_domain_and_website_url_preserves_user_input() -> None:
    from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url

    domain, url = prepare_domain_and_website_url("aibase.com", "https://geo.aibase.com/")
    assert domain == "aibase.com"
    assert url == "https://geo.aibase.com"

    domain, url = prepare_domain_and_website_url(
        "aibase.com",
        "geo.aibase.com/about",
        probe=False,
    )
    assert domain == "aibase.com"
    assert url == "geo.aibase.com/about"


def test_prepare_domain_and_website_url_skips_probe_without_explicit_url() -> None:
    from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url

    domain, url = prepare_domain_and_website_url("example.com", "", probe=False)
    assert domain == "example.com"
    assert url.startswith("https://")
    assert "example.com" in url


def test_resolve_website_without_probe() -> None:
    domain, url = resolve_website("https://www.stripe.com/pricing", probe=False)
    assert domain == "stripe.com"
    assert url == website_fallback("stripe.com")


@patch("aperix_geo.utils.url.host_resolves", return_value=False)
def test_resolve_website_probe_success(_mock_resolve: MagicMock) -> None:
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
        domain, url = resolve_website("example.com", probe=True, timeout_s=1.0)

    assert domain == "example.com"
    assert url == "https://example.com"


def test_page_url() -> None:
    assert page_url("https://Example.com/about/") == "https://example.com/about"
    assert page_url("https://example.com/pricing#x") == "https://example.com/pricing"


def test_crawl_cache_url() -> None:
    assert crawl_cache_url("https://Example.com/page/?utm_source=x&a=1") == (
        "https://example.com/page?a=1"
    )
    assert crawl_cache_url("https://example.com/page/?fbclid=abc") == "https://example.com/page"
    assert crawl_cache_url("https://example.com/page/?utm=1") == "https://example.com/page"


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


def test_apex_homepage_urls(monkeypatch) -> None:
    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"example.com", "www.example.com"},
    )
    urls = apex_homepage_urls("example.com")
    assert urls[0] == "https://example.com/"
    assert urls[1] == "https://www.example.com/"


def test_website_candidates_includes_http_fallback(monkeypatch) -> None:
    from aperix_geo.utils.url import website_candidates

    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"chinatea.com.cn", "www.chinatea.com.cn"},
    )
    urls = website_candidates("chinatea.com.cn")
    assert urls[0] == "https://www.chinatea.com.cn/"
    assert "http://www.chinatea.com.cn/" in urls
    assert "http://chinatea.com.cn/" in urls


def test_website_candidates_prefers_explicit_http_url(monkeypatch) -> None:
    from aperix_geo.utils.url import website_candidates

    monkeypatch.setattr("aperix_geo.utils.url.host_resolves", lambda host: True)
    urls = website_candidates(
        "chinatea.com.cn",
        preferred_url="http://www.chinatea.com.cn/",
    )
    assert urls[0] == "http://www.chinatea.com.cn"


def test_profile_crawl_urls_user_input_first() -> None:
    urls = profile_crawl_urls(
        "https://www.sheepgeo.com/about",
        root="sheepgeo.com",
    )
    assert urls[0] == "https://www.sheepgeo.com/about"
    assert "https://sheepgeo.com/" in urls
