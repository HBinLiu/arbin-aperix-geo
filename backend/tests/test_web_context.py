"""Unit tests for web_context URL helpers."""

from aperix_geo.services.crawl._crawl4ai import result_markdown
from aperix_geo.utils.domains import strip_hostname
from aperix_geo.utils.text import headings_from_markdown, truncate_text
from aperix_geo.utils.url import (
    homepage_urls,
    host_resolves,
    normalize_crawl_cache_url,
    normalize_page_url,
)


def test_normalize_page_url() -> None:
    assert normalize_page_url("https://Example.com/about/") == "https://example.com/about"
    assert normalize_page_url("https://example.com/pricing#x") == "https://example.com/pricing"


def test_normalize_crawl_cache_url() -> None:
    assert normalize_crawl_cache_url("https://Example.com/page/?utm_source=x&a=1") == (
        "https://example.com/page?a=1"
    )
    assert normalize_crawl_cache_url("https://example.com/page/?fbclid=abc") == "https://example.com/page"


def test_strip_hostname() -> None:
    assert strip_hostname("https://www.Stripe.com/pricing") == "stripe.com"


def test_result_markdown_from_object() -> None:
    class _Md:
        fit_markdown = "## About\n\nPayments."

    class _R:
        markdown = _Md()

    assert "Payments" in result_markdown(_R())


def test_truncate_markdown() -> None:
    out = truncate_text("x" * 100, 50)
    assert "截断" in out


def test_headings_from_markdown() -> None:
    md = "# Title\n\n## Sub"
    assert headings_from_markdown(md) == "Title | Sub"


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
    from aperix_geo.utils.url import homepage_urls_apex_first

    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"example.com", "www.example.com"},
    )
    urls = homepage_urls_apex_first("example.com")
    assert urls[0] == "https://example.com/"
    assert urls[1] == "https://www.example.com/"
