"""Single-flight favicon resolution state machine."""

from __future__ import annotations

import hashlib

from aperix_geo.services.favicon._domain import (
    FaviconMode,
    FaviconRequest,
    is_favicon_homepage_url,
    normalize_favicon_request,
)
from aperix_geo.services.favicon._fetch import resolve_favicon_network
from aperix_geo.services.favicon._storage import (
    cache_set,
    ensure_apex_alias,
    negative_cache_hit,
    negative_cache_set,
    read_cached_favicon,
)
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight
from aperix_geo.utils.net import favicon_from, is_valid_hostname, registrable_from

_DEFAULT_TIMEOUT_S = 5.0
_COALESCE_WAIT_S = 90.0


class _FaviconMiss:
    __slots__ = ()


MISS = _FaviconMiss()


def _lookup(req: FaviconRequest) -> tuple[bytes, str] | _FaviconMiss | None:
    """Mem/disk (+ apex promote for HOME apex). None = need network."""
    if req.mode is FaviconMode.HOME and negative_cache_hit(req.cache_key):
        return MISS
    if hit := read_cached_favicon(req.cache_key):
        return hit
    # Only promote onto apex when the request itself is for the apex homepage.
    if req.mode is FaviconMode.HOME and req.cache_key == req.apex:
        if promoted := ensure_apex_alias(req.apex):
            return promoted
    return None


def resolve_favicon_sync(
    req: FaviconRequest,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> tuple[bytes, str] | None:
    """Resolve one FaviconRequest: lookup → (HOME apex) promote → network → persist."""
    # HOME flights coalesce on cache_key; PAGE keeps fetch_url so articles don't block each other.
    flight_key = req.cache_key if req.mode is FaviconMode.HOME else f"{req.cache_key}|{req.fetch_url}"
    digest = hashlib.sha256(flight_key.encode()).hexdigest()

    def fetch() -> tuple[bytes, str] | _FaviconMiss:
        if req.mode is FaviconMode.HOME and req.cache_key == req.apex:
            if promoted := ensure_apex_alias(req.apex):
                return promoted
        result = resolve_favicon_network(
            req.cache_key,
            timeout_s=timeout_s,
            page_url=req.fetch_url,
            mode=req.mode,
        )
        if result is None:
            if req.mode is FaviconMode.HOME:
                negative_cache_set(req.cache_key)
            return MISS
        body, media = result
        cache_set(req.cache_key, body, media)
        return result

    try:
        out = run_single_flight(
            digest,
            wait_s=max(_COALESCE_WAIT_S, timeout_s * 4 + 30.0),
            read_cache=lambda: _lookup(req),
            fetch=fetch,
            lock_prefix="aperix:favicon:lock:",
        )
    except SingleFlightWaitTimeout:
        cached = _lookup(req)
        out = cached if cached is not None else fetch()
    return None if out is MISS else out


def resolve_favicon_coalesced(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    """Build FaviconRequest from domain + optional page_url, then resolve."""
    key = favicon_from(domain) or domain.strip().lower()
    if not key or not is_valid_hostname(key):
        return None

    raw = (page_url or "").strip() or f"https://{key}/"
    parsed = normalize_favicon_request(raw)
    fetch_url = parsed.fetch_url if parsed else f"https://{key}/"
    apex = registrable_from(key) or key
    mode = FaviconMode.HOME if is_favicon_homepage_url(fetch_url, key) else FaviconMode.PAGE
    req = FaviconRequest(cache_key=key, apex=apex, fetch_url=fetch_url, mode=mode)
    return resolve_favicon_sync(req, timeout_s=timeout_s)
