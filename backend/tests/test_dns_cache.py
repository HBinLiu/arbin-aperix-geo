"""Tests for DNS resolution cache."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from aperix_geo.utils.dns import clear_dns_cache, host_has_dns_records, host_resolves_public


@pytest.fixture(autouse=True)
def _isolate_dns_cache_from_redis() -> None:
    with (
        patch("aperix_geo.utils.dns.redis_get_json_with_remaining_ttl", return_value=None),
        patch("aperix_geo.utils.dns.redis_set_json_exat"),
    ):
        yield


def test_dns_cache_hit() -> None:
    clear_dns_cache()
    calls = {"n": 0}

    def _lookup(host: str, *, timeout_s: float) -> bool:
        calls["n"] += 1
        return host == "example.com"

    with patch("aperix_geo.utils.dns._host_has_dns_records_uncached", side_effect=_lookup):
        assert host_has_dns_records("example.com", cache_ttl_s=3600) is True
        assert host_has_dns_records("example.com", cache_ttl_s=3600) is True

    assert calls["n"] == 1


def test_dns_cache_disabled() -> None:
    clear_dns_cache()
    calls = {"n": 0}

    def _lookup(host: str, *, timeout_s: float) -> bool:
        calls["n"] += 1
        return True

    with patch("aperix_geo.utils.dns._host_has_dns_records_uncached", side_effect=_lookup):
        host_has_dns_records("example.com", cache_ttl_s=0)
        host_has_dns_records("example.com", cache_ttl_s=0)

    assert calls["n"] == 2


def test_host_resolves_public_uses_cache() -> None:
    clear_dns_cache()
    calls = {"n": 0}

    def _lookup(host: str, *, timeout_s: float) -> bool:
        calls["n"] += 1
        return True

    with patch("aperix_geo.utils.dns._host_resolves_public_uncached", side_effect=_lookup):
        assert host_resolves_public("example.com", cache_ttl_s=3600) is True
        assert host_resolves_public("example.com", cache_ttl_s=3600) is True

    assert calls["n"] == 1


@patch("aperix_geo.utils.dns._host_has_dns_records_uncached", return_value=True)
def test_host_has_dns_records_uncached_delegates(mock_uncached) -> None:
    assert host_has_dns_records("example.com", cache_ttl_s=0, timeout_s=1.0) is True
    mock_uncached.assert_called_once_with("example.com", timeout_s=1.0)
