"""Tests for unified net identity helpers."""

from __future__ import annotations

from aperix_geo.utils.net import (
    brand_from,
    citation_registrable_key,
    favicon_from,
    host_from,
    host_under_root,
    registrable_from,
)


def test_host_from_url_and_bare_host() -> None:
    assert host_from("https://www.Blog.Example.com/path") == "blog.example.com"
    assert host_from("blog.example.com") == "blog.example.com"


def test_registrable_from() -> None:
    assert registrable_from("https://blog.wise.com/x") == "wise.com"
    assert registrable_from("foo.com.cn") == "foo.com.cn"
    assert registrable_from("96.8") == ""


def test_brand_from() -> None:
    assert brand_from("https://Stripe.COM/x") == "stripe.com"
    assert brand_from("96.8") == ""


def test_registrable_from_citation_url() -> None:
    assert registrable_from("https://docs.acme-brand.com/b") == "acme-brand.com"


def test_favicon_from_keeps_subdomain() -> None:
    assert favicon_from("https://yjj.gxzf.gov.cn/") == "yjj.gxzf.gov.cn"
    assert favicon_from("https://www.wise.com/") == "wise.com"


def test_citation_registrable_key() -> None:
    assert citation_registrable_key("https://docs.stripe.com/payments") == "stripe.com"
    assert citation_registrable_key("docs.stripe.com") == "stripe.com"
    assert citation_registrable_key("stripe.com") == "stripe.com"


def test_host_under_root() -> None:
    assert host_under_root("blog.wise.com", "wise.com")
    assert not host_under_root("stripe.com", "wise.com")
