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
