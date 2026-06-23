"""Tests for URL host ↔ brand domain matching."""

from __future__ import annotations

from aperix_geo.services.sampling.mentions import host_mentions_domain


def test_host_mentions_domain_matches_subdomain() -> None:
    assert host_mentions_domain("wise.com", ["blog.wise.com"])
    assert host_mentions_domain("wise.com", ["wise.com"])


def test_host_mentions_domain_rejects_substring_false_positive() -> None:
    assert not host_mentions_domain("wise.com", ["otherwise.com"])


def test_host_mentions_domain_empty_inputs() -> None:
    assert not host_mentions_domain("", ["wise.com"])
    assert not host_mentions_domain("wise.com", [])
