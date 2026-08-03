"""Tests for cache compression and bounded L1."""

from __future__ import annotations

import time
from unittest.mock import patch
from uuid import uuid4

from aperix_geo.services.crawl._cache import (
    _compress_text,
    _decompress_text,
    _pack_redis_fields,
    _page_memory,
    _unpack_redis_fields,
    clear_page_cache,
    get_cached_page,
    set_cached_page,
    set_negative_cached_page,
)
from aperix_geo.services.crawl.types import PageFetchResult
from aperix_geo.services.sampling.citation.cache.page_meta import (
    clear_job_citation_pages_for_job,
    get_job_citation_page,
    set_job_citation_page,
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


def test_pack_redis_fields_idempotent() -> None:
    html = "<html>" + ("y" * 5000) + "</html>"
    once = _pack_redis_fields({"html": html, "markdown": ""})
    twice = _pack_redis_fields(once)
    assert twice["html"] == once["html"]
    assert _unpack_redis_fields(twice)["html"] == html


def test_page_l1_skips_successful_html_body() -> None:
    clear_page_cache()
    html = "<html><body>" + ("z" * 6000) + "</body></html>"
    result = PageFetchResult(
        url="https://example.com/mem",
        final_url="https://example.com/mem",
        http_status=200,
        html=html,
        source="httpx",
    )
    packed = None

    def _capture_redis(_key, payload, *, expires_at):
        nonlocal packed
        packed = payload

    with patch("aperix_geo.services.crawl._cache.redis_set_json_exat", side_effect=_capture_redis):
        set_cached_page(
            result.url,
            result,
            max_chars=32_000,
            crawl_fallback=True,
            ttl_s=3600,
        )

    assert _page_memory._data == {}
    assert packed is not None
    assert isinstance(packed["html"], dict)

    with patch(
        "aperix_geo.services.crawl._cache.redis_get_json_with_remaining_ttl",
        return_value=(packed, 3600),
    ):
        hit = get_cached_page(
            result.url,
            max_chars=32_000,
            crawl_fallback=True,
            ttl_s=3600,
        )
    assert hit is not None
    assert hit.html == html
    # Successful hydrate must not populate process L1 with HTML.
    assert _page_memory._data == {}
    clear_page_cache()


def test_page_l1_keeps_negative_marker() -> None:
    clear_page_cache()
    with patch("aperix_geo.services.crawl._cache.redis_set_json_exat"):
        set_negative_cached_page(
            "https://example.com/neg",
            max_chars=32_000,
            crawl_fallback=True,
            negative_ttl_s=60,
        )
    assert any(v[1].get("negative") for v in _page_memory._data.values())
    with patch(
        "aperix_geo.services.crawl._cache.redis_get_json_with_remaining_ttl",
        return_value=None,
    ):
        hit = get_cached_page(
            "https://example.com/neg",
            max_chars=32_000,
            crawl_fallback=True,
            ttl_s=3600,
            negative_ttl_s=60,
        )
    assert hit is not None
    assert not hit.fetch_ok
    clear_page_cache()


def test_bounded_ttl_cache_evicts_oldest() -> None:
    cache = BoundedTTLCache(2)
    now = int(time.time()) + 60
    cache.set("a", 1, expires_at=now)
    cache.set("b", 2, expires_at=now)
    cache.set("c", 3, expires_at=now)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_bounded_ttl_cache_clear_prefix() -> None:
    cache = BoundedTTLCache(10)
    now = int(time.time()) + 60
    cache.set("job-a:u1", 1, expires_at=now)
    cache.set("job-a:u2", 2, expires_at=now)
    cache.set("job-b:u1", 3, expires_at=now)
    assert cache.clear_prefix("job-a:") == 2
    assert cache.get("job-a:u1") is None
    assert cache.get("job-b:u1") == 3


def test_clear_job_citation_pages_for_job_only_touches_that_job(monkeypatch) -> None:
    job_a = uuid4()
    job_b = uuid4()
    monkeypatch.setattr(
        "aperix_geo.services.sampling.citation.cache.page_meta._job_page_cache_ttl_s",
        lambda: 3600,
    )
    monkeypatch.setattr(
        "aperix_geo.utils.cache.tiered_json.redis_set_json_exat",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "aperix_geo.utils.cache.tiered_json.redis_get_json",
        lambda *args, **kwargs: None,
    )
    set_job_citation_page(job_a, {"url": "https://a.example/1", "title": "A"})
    set_job_citation_page(job_b, {"url": "https://b.example/1", "title": "B"})
    assert clear_job_citation_pages_for_job(job_a) >= 1
    assert get_job_citation_page(job_a, "https://a.example/1") is None
    assert get_job_citation_page(job_b, "https://b.example/1") is not None
