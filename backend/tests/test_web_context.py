"""Unit tests for web_context URL helpers."""

from aperix_geo.services.web_context import _result_markdown
from aperix_geo.utils.domains import strip_hostname
from aperix_geo.utils.text import headings_from_markdown, truncate_text
from aperix_geo.utils.url import homepage_urls, host_resolves, normalize_page_url


def test_normalize_page_url() -> None:
    assert normalize_page_url("https://Example.com/about/") == "https://example.com/about"
    assert normalize_page_url("https://example.com/pricing#x") == "https://example.com/pricing"


def test_strip_hostname() -> None:
    assert strip_hostname("https://www.Stripe.com/pricing") == "stripe.com"


def test_result_markdown_from_object() -> None:
    class _Md:
        fit_markdown = "## About\n\nPayments."

    class _R:
        markdown = _Md()

    assert "Payments" in _result_markdown(_R())


def test_truncate_markdown() -> None:
    out = truncate_text("x" * 100, 50)
    assert "截断" in out


def test_headings_from_markdown() -> None:
    md = "# Title\n\n## Sub"
    assert headings_from_markdown(md) == "Title | Sub"


def test_host_resolves_invalid() -> None:
    assert not host_resolves("this-domain-definitely-does-not-exist-aperix.test")


def test_homepage_urls_prefers_www() -> None:
    urls = homepage_urls("shushangyun.com")
    assert urls[0] == "https://www.shushangyun.com/"
    assert all(u.startswith("https://") for u in urls)
