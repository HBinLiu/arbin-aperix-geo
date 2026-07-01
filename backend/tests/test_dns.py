"""Tests for dnspython-based DNS helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dns.resolver
import pytest

from aperix_geo.utils.dns import (
    clear_dns_cache,
    dns_timeout_s,
    host_has_dns_records,
    host_resolves_public,
    registrable_root_has_dns,
    resolve_host_addresses,
)


@pytest.fixture(autouse=True)
def _dns_test_isolation() -> None:
    """Avoid cross-test DNS L1 cache hits masking resolver mocks."""
    clear_dns_cache()
    yield
    clear_dns_cache()


@patch("aperix_geo.config.get_settings")
def test_dns_timeout_s_reads_config(mock_settings) -> None:
    mock_settings.return_value.dns_timeout_s = 1.0
    assert dns_timeout_s() == 1.0
    mock_settings.return_value.dns_timeout_s = 1.5
    assert dns_timeout_s() == 1.5


@patch("aperix_geo.config.get_settings")
def test_dns_cache_ttl_s_reads_config(mock_settings) -> None:
    from aperix_geo.utils.dns import dns_cache_ttl_s

    mock_settings.return_value.dns_cache_ttl_s = 3600
    assert dns_cache_ttl_s() == 3600


@patch("aperix_geo.config.get_settings")
@patch("dns.resolver.Resolver.resolve")
def test_host_has_dns_records_true_on_a_record(mock_resolve: MagicMock, mock_settings) -> None:
    mock_settings.return_value.dns_cache_ttl_s = 0
    mock_resolve.return_value = [MagicMock()]
    assert host_has_dns_records("stripe.com") is True
    mock_resolve.assert_called_once_with("stripe.com", "A")


@patch("dns.resolver.Resolver.resolve")
def test_host_has_dns_records_false_on_nxdomain(mock_resolve: MagicMock) -> None:
    mock_resolve.side_effect = dns.resolver.NXDOMAIN()
    assert host_has_dns_records("missing.example") is False


@patch("aperix_geo.config.get_settings")
@patch("dns.resolver.Resolver.resolve")
def test_host_has_dns_records_tries_aaaa_after_no_answer(mock_resolve: MagicMock, mock_settings) -> None:
    mock_settings.return_value.dns_cache_ttl_s = 0
    mock_resolve.side_effect = [dns.resolver.NoAnswer(), [MagicMock()]]
    assert host_has_dns_records("ipv6-only.example") is True
    assert mock_resolve.call_count == 2


@patch("aperix_geo.utils.dns.host_has_dns_records")
def test_registrable_root_has_dns_checks_www_fallback(mock_has: MagicMock) -> None:
    mock_has.side_effect = [False, True]
    assert registrable_root_has_dns("stripe.com") is True
    assert mock_has.call_args_list[0].args == ("stripe.com",)
    assert mock_has.call_args_list[1].args == ("www.stripe.com",)


@patch("aperix_geo.utils.dns.host_has_dns_records", return_value=False)
def test_registrable_root_has_dns_rejects_invalid_format(_mock_has: MagicMock) -> None:
    assert registrable_root_has_dns("96.8") is False


@patch("dns.resolver.Resolver.resolve")
def test_resolve_host_addresses_collects_a_and_aaaa(mock_resolve: MagicMock) -> None:
    a_record = MagicMock()
    a_record.address = "93.184.216.34"
    aaaa_record = MagicMock()
    aaaa_record.address = "2001:db8::1"
    mock_resolve.side_effect = [[a_record], [aaaa_record]]

    assert resolve_host_addresses("example.com") == ["93.184.216.34", "2001:db8::1"]


@patch("aperix_geo.utils.dns.resolve_host_addresses")
def test_host_resolves_public_rejects_private(mock_addrs: MagicMock) -> None:
    mock_addrs.side_effect = lambda host, **kwargs: (
        ["10.0.0.1"] if host == "internal.example" else ["93.184.216.34"]
    )
    assert host_resolves_public("internal.example") is False
    assert host_resolves_public("wise.com") is True
