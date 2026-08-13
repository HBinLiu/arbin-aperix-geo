"""DNS lookups via dnspython (with optional L1 + Redis cache)."""

from __future__ import annotations

import hashlib
import ipaddress
import time
from collections.abc import Callable

from aperix_geo.utils.cache.bounded import BoundedTTLCache
from aperix_geo.utils.cache.ttl import expires_at_from_ttl

# Redis helpers are imported lazily inside functions that need them.

_DNS_L1_MAX = 2048
_dns_memory = BoundedTTLCache(_DNS_L1_MAX)
_DNS_REDIS_PREFIX = "aperix:dns:v1:"


def dns_timeout_s() -> float:
    """Project-wide DNS query timeout (``Settings.dns_timeout_s`` / ``DNS_TIMEOUT_S``)."""
    from aperix_geo.config import get_settings

    return get_settings().dns_timeout_s


def dns_cache_ttl_s() -> int:
    """DNS lookup cache TTL (``Settings.dns_cache_ttl_s`` / ``DNS_CACHE_TTL_S``); 0=off."""
    from aperix_geo.config import get_settings

    return get_settings().dns_cache_ttl_s


def _effective_timeout(timeout_s: float | None) -> float:
    return dns_timeout_s() if timeout_s is None else timeout_s


def _effective_cache_ttl(cache_ttl_s: int | None) -> int:
    return dns_cache_ttl_s() if cache_ttl_s is None else cache_ttl_s


def _normalized_host(host: str) -> str:
    return (host or "").strip().lower().rstrip(".")


def _dns_redis_key(cache_key: str) -> str:
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return f"{_DNS_REDIS_PREFIX}{digest}"


def _cached_bool(
    cache_key: str,
    *,
    cache_ttl_s: int | None,
    lookup: Callable[[], bool],
) -> bool:
    ttl = _effective_cache_ttl(cache_ttl_s)
    if ttl <= 0:
        return lookup()

    cached = _dns_memory.get(cache_key)
    if cached is not None:
        return bool(cached)

    hit = None
    from aperix_geo.utils.cache.redis_kv import (
        redis_get_json_with_remaining_ttl,
        redis_set_json_exat,
    )

    hit = redis_get_json_with_remaining_ttl(_dns_redis_key(cache_key))
    if hit is not None:
        data, remaining = hit
        if "ok" in data:
            ok = bool(data["ok"])
            expires_at = int(data.get("expires_at") or (time.time() + remaining))
            _dns_memory.set(cache_key, ok, expires_at=expires_at)
            return ok

    ok = lookup()
    expires_at = expires_at_from_ttl(ttl)
    _dns_memory.set(cache_key, ok, expires_at=expires_at)
    redis_set_json_exat(_dns_redis_key(cache_key), {"ok": ok, "expires_at": expires_at}, expires_at=expires_at)
    return ok


def clear_dns_cache() -> None:
    _dns_memory.clear()


def _make_resolver(*, timeout_s: float):
    import dns.resolver

    resolver = dns.resolver.Resolver(configure=True)
    resolver.lifetime = timeout_s
    return resolver


def _dns_lookup_failed(exc: BaseException) -> bool:
    import dns.exception
    import dns.resolver

    return isinstance(
        exc,
        (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout,
            dns.exception.Timeout,
            OSError,
        ),
    )


def _resolve_host_addresses_uncached(host: str, *, timeout_s: float) -> list[str]:
    import dns.exception
    import dns.resolver

    resolver = _make_resolver(timeout_s=timeout_s)
    addresses: list[str] = []

    for rdtype in ("A", "AAAA"):
        try:
            answers = resolver.resolve(host, rdtype)
        except dns.resolver.NXDOMAIN:
            return []
        except dns.resolver.NoAnswer:
            continue
        except dns.exception.DNSException as exc:
            if _dns_lookup_failed(exc):
                return []
            return []
        for rdata in answers:
            addresses.append(rdata.address)
    return addresses


def resolve_host_addresses(host: str, *, timeout_s: float | None = None) -> list[str]:
    """Return A/AAAA addresses for a host (follows CNAME via dnspython)."""
    key = _normalized_host(host)
    if not key:
        return []
    effective = _effective_timeout(timeout_s)
    return _resolve_host_addresses_uncached(key, timeout_s=effective)


def _host_has_dns_records_uncached(host: str, *, timeout_s: float) -> bool:
    import dns.exception
    import dns.resolver

    resolver = _make_resolver(timeout_s=timeout_s)

    for rdtype in ("A", "AAAA", "CNAME"):
        try:
            resolver.resolve(host, rdtype)
            return True
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.NoAnswer:
            continue
        except dns.exception.DNSException as exc:
            if _dns_lookup_failed(exc):
                return False
            return False
    return False


def host_has_dns_records(
    host: str,
    *,
    timeout_s: float | None = None,
    cache_ttl_s: int | None = None,
) -> bool:
    """True when the host has at least one A, AAAA, or CNAME record."""
    key = _normalized_host(host)
    if not key:
        return False
    effective = _effective_timeout(timeout_s)
    return _cached_bool(
        f"records:{key}",
        cache_ttl_s=cache_ttl_s,
        lookup=lambda: _host_has_dns_records_uncached(key, timeout_s=effective),
    )


def _host_resolves_public_uncached(host: str, *, timeout_s: float) -> bool:
    addresses = _resolve_host_addresses_uncached(host, timeout_s=timeout_s)
    if not addresses:
        return False
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True


def host_resolves_public(
    host: str,
    *,
    timeout_s: float | None = None,
    cache_ttl_s: int | None = None,
) -> bool:
    """True when DNS resolves and every A/AAAA address is a public routable IP."""
    key = _normalized_host(host)
    if not key:
        return False
    effective = _effective_timeout(timeout_s)
    return _cached_bool(
        f"public:{key}",
        cache_ttl_s=cache_ttl_s,
        lookup=lambda: _host_resolves_public_uncached(key, timeout_s=effective),
    )


def registrable_root_has_dns(domain: str, *, timeout_s: float | None = None, cache_ttl_s: int | None = None) -> bool:
    """True when the eTLD+1 (or its www host) has DNS records."""
    from aperix_geo.utils.domains import brand_from

    root = brand_from(domain)
    if not root:
        return False
    if host_has_dns_records(root, timeout_s=timeout_s, cache_ttl_s=cache_ttl_s):
        return True
    return host_has_dns_records(f"www.{root}", timeout_s=timeout_s, cache_ttl_s=cache_ttl_s)
