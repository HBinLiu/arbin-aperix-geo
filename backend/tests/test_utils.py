"""Tests for shared utility helpers (coerce, text, url, contact, datetime, domains)."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

import pytest

from aperix_geo.utils.coerce import pick_str, safe_float, safe_int
from aperix_geo.utils.contact import normalize_email, normalize_phone_cn
from aperix_geo.utils.datetime import parse_iso_datetime
from aperix_geo.utils.domains import (
    brand_from,
    dedupe_domains,
    ensure_brand,
    is_brand_domain,
    normalize_host,
    registrable_domain,
    site_name_from_title,
    title_alias_candidates,
    strip_hostname,
)
from aperix_geo.utils.text import headings_from_markdown, normalize_whitespace, prompt_text_hash, truncate_text
from aperix_geo.utils.url import (
    extract_urls,
    filter_citation_urls,
    host_from_url,
    host_resolves_public,
    host_under_root,
    is_citation_host,
    is_placeholder_citation_host,
    parse_url,
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


def test_host_from_url_strips_port_and_www() -> None:
    assert host_from_url("https://www.Example.com:443/path") == "example.com"


def test_normalize_host() -> None:
    assert normalize_host("WWW.Example.COM") == "example.com"
    assert normalize_host("https://blog.Example.com/path") == "blog.example.com"
    assert normalize_host("") == ""
    assert normalize_host(None) == ""


def test_parse_url_validates() -> None:
    assert parse_url("https://wise.com/path") == "https://wise.com/path"
    assert parse_url("geo.aibase.com/about") == "https://geo.aibase.com/about"
    assert parse_url("not-a-url") == ""


def test_host_under_root() -> None:
    assert host_under_root("www.blog.example.com", "example.com")
    assert not host_under_root("other.com", "example.com")


def test_is_placeholder_citation_host() -> None:
    assert is_placeholder_citation_host("example.com")
    assert is_placeholder_citation_host("blog.example.com")
    assert is_placeholder_citation_host("www.example.org")
    assert is_placeholder_citation_host("localhost")
    assert not is_placeholder_citation_host("wise.com")
    assert not is_placeholder_citation_host("11467.com")


def test_is_citation_host_rejects_numeric_scores() -> None:
    assert not is_citation_host("9.8")
    assert not is_citation_host("9.5")
    assert not is_citation_host("9.2")
    assert not is_citation_host("0.5")
    assert not is_citation_host("1.75")
    assert not is_citation_host("0.0.0.5")
    assert not is_citation_host("3.0.0.1")
    assert is_citation_host("wise.com")
    assert is_citation_host("11467.com")
    assert not is_citation_host("jiqiz")
    assert not is_citation_host("localhost")


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


def test_host_resolves_public_rejects_private() -> None:
    from aperix_geo.utils.url import host_resolves_public

    with patch("aperix_geo.utils.dns.resolve_host_addresses") as mock_addrs:
        mock_addrs.side_effect = lambda host, **kwargs: (
            ["10.0.0.1"] if host == "internal.example" else ["93.184.216.34"]
        )
        assert host_resolves_public("internal.example") is False
        assert host_resolves_public("wise.com") is True


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


def test_is_brand_domain() -> None:
    assert is_brand_domain("stripe.com")
    assert is_brand_domain("https://www.163.com/path")
    assert is_brand_domain("3m.com")
    assert is_brand_domain("foo.co.uk")
    assert is_brand_domain("brand.xn--p1ai")

    assert not is_brand_domain("96.8")
    assert not is_brand_domain("99.5")
    assert not is_brand_domain("192.168.1.1")
    assert not is_brand_domain("10.0.0.1")
    assert not is_brand_domain("foo.8")
    assert not is_brand_domain("")
    assert not is_brand_domain("not-a-host")


def test_brand_from() -> None:
    assert brand_from("https://Stripe.COM/x") == "stripe.com"
    assert brand_from("96.8") == ""
    assert brand_from("  ") == ""


def test_site_name_from_title_chinese() -> None:
    assert site_name_from_title("万里汇 | 跨境支付平台", domain="wise.com") == "万里汇"


def test_site_name_from_title_empty_falls_back_to_domain() -> None:
    assert site_name_from_title("", domain="wise.com") == "wise.com"
    assert site_name_from_title("", domain="business.wise.com") == "wise.com"


def test_title_alias_candidates_from_chinese_title() -> None:
    aliases = title_alias_candidates("万里汇 | 跨境支付平台", domain="wise.com", brand="Wise")
    assert "万里汇" in aliases
    assert "跨境支付平台" in aliases
    assert "Wise" not in aliases


def test_title_alias_candidates_space_separated_chinese() -> None:
    aliases = title_alias_candidates("万里汇 跨境支付平台", domain="wise.com", brand="Wise")
    assert "万里汇" in aliases
    assert "跨境支付平台" in aliases


def test_title_alias_candidates_space_separated_latin() -> None:
    aliases = title_alias_candidates("NewCo Platform", domain="new.com", brand="new.com")
    assert "NewCo" in aliases
    assert "Platform" not in aliases


def test_title_alias_candidates_skips_latin_descriptions() -> None:
    aliases = title_alias_candidates("PayPal: Send Money", domain="paypal.com", brand="PayPal")
    assert aliases == []


def test_ensure_brand_uses_domain_fallback() -> None:
    assert ensure_brand("", domain="www.paypal.com") == "paypal.com"
    assert ensure_brand("PayPal", domain="paypal.com") == "PayPal"


def test_competitor_item_website_url_http_validation() -> None:
    from pydantic import ValidationError

    from aperix_geo.schemas.catalog import CompetitorItem

    item = CompetitorItem(domain="wise.com", brand="Wise", website_url="https://wise.com/path")
    assert str(item.website_url).startswith("https://")

    assert CompetitorItem(domain="wise.com", brand="Wise", website_url="").website_url == ""

    with pytest.raises(ValidationError):
        CompetitorItem(domain="wise.com", brand="Wise", website_url="not-a-url")
