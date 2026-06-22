"""Coalesced favicon resolution (single-flight + negative cache)."""

from __future__ import annotations

import hashlib

from aperix_geo.services.favicon._domain import is_favicon_homepage_url
from aperix_geo.services.favicon._fetch import resolve_favicon_network
from aperix_geo.services.favicon._storage import (
    cache_set,
    negative_cache_hit,
    negative_cache_set,
    read_cached_favicon,
)
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight


class _FaviconMiss:
    """Sentinel: domain known to have no favicon (negative cache)."""

    __slots__ = ()


MISS = _FaviconMiss()

_DEFAULT_TIMEOUT_S = 5.0
_COALESCE_WAIT_S = 90.0


def _read_cached(domain: str, *, page_url: str | None = None) -> tuple[bytes, str] | _FaviconMiss | None:
    if (not page_url or is_favicon_homepage_url(page_url, domain)) and negative_cache_hit(domain):
        return MISS
    return read_cached_favicon(domain)


def resolve_favicon_coalesced(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    """Resolve favicon once per domain under concurrent requests."""
    digest = hashlib.sha256(f"{domain}|{page_url or ''}".encode()).hexdigest()

    def fetch() -> tuple[bytes, str] | _FaviconMiss:
        result = resolve_favicon_network(domain, timeout_s=timeout_s, page_url=page_url)
        if result is None:
            if not page_url or is_favicon_homepage_url(page_url, domain):
                negative_cache_set(domain)
            return MISS
        body, media = result
        cache_set(domain, body, media)
        return result

    try:
        out = run_single_flight(
            digest,
            wait_s=max(_COALESCE_WAIT_S, timeout_s * 4 + 30.0),
            read_cache=lambda: _read_cached(domain, page_url=page_url),
            fetch=fetch,
            lock_prefix="aperix:favicon:lock:",
        )
    except SingleFlightWaitTimeout:
        cached = _read_cached(domain, page_url=page_url)
        if cached is not None:
            out = cached
        else:
            out = fetch()
    return None if out is MISS else out
