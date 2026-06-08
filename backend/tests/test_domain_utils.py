"""Tests for domain normalization helpers."""

from aperix_geo.utils.domains import (
    dedupe_domains,
    registrable_domain,
    site_name_from_title,
    strip_hostname,
)


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
    from aperix_geo.utils.domains import ensure_brand

    assert ensure_brand("", domain="www.paypal.com") == "paypal.com"
    assert ensure_brand("PayPal", domain="paypal.com") == "PayPal"
