"""Tests for shared utility helpers (coerce, text, url, contact, datetime, domains)."""

from __future__ import annotations

from datetime import UTC

import pytest

from aperix_geo.utils.coerce import pick_str, safe_float, safe_int
from aperix_geo.utils.contact import normalize_email, normalize_phone_cn
from aperix_geo.utils.datetime import parse_iso_datetime
from aperix_geo.utils.domains import (
    dedupe_domains,
    ensure_brand,
    registrable_domain,
    site_name_from_title,
    strip_hostname,
)
from aperix_geo.utils.text import headings_from_markdown, normalize_whitespace, prompt_text_hash, truncate_text
from aperix_geo.utils.url import (
    extract_urls,
    filter_citation_urls,
    host_matches_root,
    hostname_from_url,
    is_placeholder_citation_host,
    is_valid_citation_host,
    normalize_domain,
)


# --- coerce ---


def test_safe_int() -> None:
    assert safe_int({"n": "3"}, "n") == 3
    assert safe_int({"n": "x"}, "n", default=7) == 7
    assert safe_int({}, "missing", default=1) == 1


def test_safe_float() -> None:
    assert safe_float({"n": "1.5"}, "n") == 1.5
    assert safe_float({}, "n") is None
    assert safe_float({"n": "bad"}, "n") is None


def test_pick_str() -> None:
    data = {"title": "  Hello ", "empty": "   "}
    assert pick_str(data, "missing", "title") == "Hello"
    assert pick_str(data, "empty", "missing") == ""


# --- text ---


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("  hello   world \n") == "hello world"


def test_truncate_text() -> None:
    out = truncate_text("x" * 100, 50)
    assert "截断" in out
    assert len(out) == 50


def test_prompt_text_hash_normalizes_whitespace() -> None:
    assert prompt_text_hash("  a  b ") == prompt_text_hash("a b")


def test_headings_from_markdown() -> None:
    md = "# Title\n\n## Sub\n\n### Skip extra"
    assert headings_from_markdown(md, limit=2) == "Title | Sub"


# --- url ---


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


def test_is_valid_citation_host_rejects_numeric_scores() -> None:
    assert not is_valid_citation_host("9.8")
    assert not is_valid_citation_host("9.5")
    assert not is_valid_citation_host("9.2")
    assert not is_valid_citation_host("0.5")
    assert not is_valid_citation_host("1.75")
    assert not is_valid_citation_host("0.0.0.5")
    assert not is_valid_citation_host("3.0.0.1")
    assert is_valid_citation_host("wise.com")
    assert is_valid_citation_host("11467.com")


def test_is_llm_numeric_fake_url() -> None:
    from aperix_geo.utils.url import is_llm_numeric_fake_url

    assert is_llm_numeric_fake_url("https://0.5/")
    assert is_llm_numeric_fake_url("https://1.75/")
    assert is_llm_numeric_fake_url("https://0.0.0.5/")
    assert not is_llm_numeric_fake_url("https://wise.com/page")
    assert not is_llm_numeric_fake_url("https://example.com/page")
    assert not is_llm_numeric_fake_url("/relative/path")


def test_filter_citation_urls() -> None:
    urls = filter_citation_urls(
        [
            "https://example.com/a",
            "https://9.8/",
            "https://9.5/path",
            "https://wise.com/b",
            "https://wise.com/b",
        ]
    )
    assert urls == ["https://wise.com/b"]


# --- contact ---


def test_normalize_email() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_normalize_email_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


def test_normalize_phone_cn() -> None:
    assert normalize_phone_cn("+86 13800138000") == "13800138000"


def test_normalize_phone_cn_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_phone_cn("12345")


# --- datetime ---


def test_parse_iso_datetime_z_suffix() -> None:
    dt = parse_iso_datetime("2024-01-15T08:00:00Z")
    assert dt.tzinfo == UTC


def test_parse_iso_datetime_naive_gets_utc() -> None:
    dt = parse_iso_datetime("2024-01-15T08:00:00")
    assert dt.tzinfo == UTC


# --- domains ---


def test_strip_hostname() -> None:
    assert strip_hostname("https://www.Stripe.com/pricing") == "stripe.com"


def test_registrable_domain() -> None:
    assert registrable_domain("business.wise.com") == "wise.com"
    assert registrable_domain("www.paypal.com") == "paypal.com"
    assert registrable_domain("foo.com.cn") == "foo.com.cn"


def test_dedupe_domains() -> None:
    assert dedupe_domains(["wise.com", "www.wise.com", "business.wise.com"]) == ["wise.com"]


def test_site_name_from_title_chinese() -> None:
    assert site_name_from_title("万里汇 | 跨境支付平台", domain="wise.com") == "万里汇"


def test_site_name_from_title_empty_falls_back_to_domain() -> None:
    assert site_name_from_title("", domain="wise.com") == "wise.com"
    assert site_name_from_title("", domain="business.wise.com") == "wise.com"


def test_ensure_brand_uses_domain_fallback() -> None:
    assert ensure_brand("", domain="www.paypal.com") == "paypal.com"
    assert ensure_brand("PayPal", domain="paypal.com") == "PayPal"
