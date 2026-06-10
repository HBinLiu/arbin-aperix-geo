"""Tests for TieredJsonCache."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.utils.cache import TieredJsonCache


def test_tiered_json_cache_l1_roundtrip() -> None:
    cache = TieredJsonCache(redis_prefix="test:tiered:", use_remaining_ttl=False)
    cache.clear()
    cache.set("key", {"value": 1}, ttl_s=60)
    payload = cache.get("key", is_valid=lambda data: "value" in data)
    assert payload is not None
    assert payload["value"] == 1


@patch("aperix_geo.utils.cache.tiered_json.redis_set_json_exat")
@patch("aperix_geo.utils.cache.tiered_json.redis_get_json", return_value=None)
def test_tiered_json_cache_strips_expires_on_read(_mock_get: object, _mock_set: object) -> None:
    cache = TieredJsonCache(
        redis_prefix="test:tiered:strip:",
        strip_expires_on_read=True,
        use_remaining_ttl=False,
    )
    cache.clear()
    cache.set("key", {"value": 2}, ttl_s=60)
    payload = cache.get("key")
    assert payload == {"value": 2}
    assert "expires_at" not in payload


def test_tiered_json_cache_skip_if_on_set() -> None:
    cache = TieredJsonCache(redis_prefix="test:tiered:skip:", use_remaining_ttl=False)
    cache.clear()
    cache.set("key", {"analysis_source": "failed"}, ttl_s=60, skip_if=lambda d: d.get("analysis_source") == "failed")
    assert cache.get("key") is None
