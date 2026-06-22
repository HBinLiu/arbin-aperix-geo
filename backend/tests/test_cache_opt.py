"""Tests for cache compression and bounded L1."""

from __future__ import annotations

import time

from aperix_geo.services.crawl._cache import (
    _compress_text,
    _decompress_text,
    _pack_redis_fields,
    _unpack_redis_fields,
)
from aperix_geo.utils.cache import BoundedTTLCache


def test_compress_roundtrip() -> None:
    text = "hello " * 2000
    packed = _compress_text(text)
    assert isinstance(packed, dict)
    assert _decompress_text(packed) == text


def test_small_text_not_compressed() -> None:
    assert _compress_text("short") == "short"


def test_pack_page_fields() -> None:
    html = "<html>" + ("x" * 5000) + "</html>"
    packed = _pack_redis_fields({"html": html, "markdown": "", "source": "httpx"})
    assert isinstance(packed["html"], dict)
    restored = _unpack_redis_fields(packed)
    assert restored["html"] == html


def test_bounded_ttl_cache_evicts_oldest() -> None:
    cache = BoundedTTLCache(2)
    now = int(time.time()) + 60
    cache.set("a", 1, expires_at=now)
    cache.set("b", 2, expires_at=now)
    cache.set("c", 3, expires_at=now)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3

