"""Tests for DNS resolution cache."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from aperix_geo.services.crawl._cache import clear_dns_cache, host_resolves_cached


@pytest.fixture(autouse=True)
def _isolate_dns_cache_from_redis() -> None:
    with (
        patch("aperix_geo.services.crawl._cache.redis_get_json_with_remaining_ttl", return_value=None),
        patch("aperix_geo.services.crawl._cache.redis_set_json_exat"),
    ):
        yield


def test_dns_cache_hit() -> None:
    clear_dns_cache()
    calls = {"n": 0}

    def _lookup(host: str, *, timeout_s: float) -> bool:
        calls["n"] += 1
        return host == "example.com"

    with patch("aperix_geo.services.crawl._cache._lookup_dns", side_effect=_lookup):
        assert host_resolves_cached("example.com", ttl_s=3600) is True
        assert host_resolves_cached("example.com", ttl_s=3600) is True

    assert calls["n"] == 1


def test_dns_cache_disabled() -> None:
    clear_dns_cache()
    calls = {"n": 0}

    def _lookup(host: str, *, timeout_s: float) -> bool:
        calls["n"] += 1
        return True

    with patch("aperix_geo.services.crawl._cache._lookup_dns", side_effect=_lookup):
        host_resolves_cached("example.com", ttl_s=0)
        host_resolves_cached("example.com", ttl_s=0)

    assert calls["n"] == 2
