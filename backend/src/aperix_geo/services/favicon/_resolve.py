"""Coalesced favicon resolution (single-flight + negative cache)."""

from __future__ import annotations

import hashlib

from aperix_geo.services.favicon._fetch import resolve_favicon_network
from aperix_geo.services.favicon._storage import (
    cache_get,
    cache_set,
    load_primary_from_disk,
    negative_cache_hit,
    negative_cache_set,
)
from aperix_geo.utils.cache import run_single_flight


class _FaviconMiss:
    """Sentinel: domain known to have no favicon (negative cache)."""

    __slots__ = ()


MISS = _FaviconMiss()

_DEFAULT_TIMEOUT_S = 5.0
_COALESCE_WAIT_S = 90.0


def _read_cached(host: str, *, page_url: str | None = None) -> tuple[bytes, str] | _FaviconMiss | None:
    if not page_url and negative_cache_hit(host):
        return MISS
    if row := cache_get(host):
        return row
    if stored := load_primary_from_disk(host):
        body, media = stored
        cache_set(host, body, media)
        return stored
    return None


def resolve_favicon_coalesced(
    host: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    """Resolve favicon once per domain under concurrent requests."""
    digest = hashlib.sha256(f"{host}|{page_url or ''}".encode()).hexdigest()

    def fetch() -> tuple[bytes, str] | _FaviconMiss:
        result = resolve_favicon_network(host, timeout_s=timeout_s, page_url=page_url)
        if result is None:
            if not page_url:
                negative_cache_set(host)
            return MISS
        body, media = result
        cache_set(host, body, media)
        return result

    out = run_single_flight(
        digest,
        wait_s=max(_COALESCE_WAIT_S, timeout_s * 4 + 30.0),
        read_cache=lambda: _read_cached(host, page_url=page_url),
        fetch=fetch,
        lock_prefix="aperix:favicon:lock:",
    )
    return None if out is MISS else out
