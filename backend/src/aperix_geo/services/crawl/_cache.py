"""L1 memory + L2 Redis TTL caches for page crawl (fetch results + DNS preflight)."""

from __future__ import annotations

import base64
import gzip
import hashlib
import logging
import socket
import time
from typing import TYPE_CHECKING, Any

from aperix_geo.utils.cache import (
    BoundedTTLCache,
    expires_at_from_ttl,
    redis_get_json_with_remaining_ttl,
    redis_set_json_exat,
)
from aperix_geo.utils.url import normalize_crawl_cache_url

if TYPE_CHECKING:
    from aperix_geo.services.crawl.types import PageFetchResult

logger = logging.getLogger(__name__)

# --- Page fetch cache ---

_PAGE_L1_MAX = 256
_COMPRESS_MIN_CHARS = 4096
_page_memory = BoundedTTLCache(_PAGE_L1_MAX)
_PAGE_REDIS_PREFIX = "aperix:page_crawl:v1:"


def _compress_text(value: str) -> str | dict[str, str]:
    if len(value) < _COMPRESS_MIN_CHARS:
        return value
    blob = gzip.compress(value.encode("utf-8"), compresslevel=6)
    return {"__gz__": base64.b64encode(blob).decode("ascii")}


def _decompress_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("__gz__"), str):
        raw = base64.b64decode(value["__gz__"])
        return gzip.decompress(raw).decode("utf-8")
    return str(value or "")


def _pack_redis_fields(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    html = str(out.get("html") or "")
    if html:
        out["html"] = _compress_text(html)
    markdown = str(out.get("markdown") or "")
    if markdown:
        out["markdown"] = _compress_text(markdown)
    return out


def _unpack_redis_fields(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["html"] = _decompress_text(out.get("html"))
    out["markdown"] = _decompress_text(out.get("markdown"))
    return out


def _logical_key(url: str, *, max_chars: int, crawl_fallback: bool) -> str:
    normalized = normalize_crawl_cache_url(url)
    return f"{normalized}|{max_chars}|{int(crawl_fallback)}"


def _digest(logical: str) -> str:
    return hashlib.sha256(logical.encode("utf-8")).hexdigest()


def logical_key_digest(url: str, *, max_chars: int, crawl_fallback: bool) -> str:
    return _digest(_logical_key(url, max_chars=max_chars, crawl_fallback=crawl_fallback))


def _page_redis_key(logical: str) -> str:
    return f"{_PAGE_REDIS_PREFIX}{_digest(logical)}"


def _page_to_dict(result: PageFetchResult) -> dict[str, Any]:
    return {
        "url": result.url,
        "final_url": result.final_url,
        "http_status": result.http_status,
        "html": result.html,
        "markdown": result.markdown,
        "source": result.source,
    }


def _page_from_dict(data: dict[str, Any]) -> PageFetchResult:
    from aperix_geo.services.crawl.types import PageFetchResult

    source = data.get("source", "none")
    if source not in ("httpx", "crawl4ai", "none"):
        source = "none"
    return PageFetchResult(
        url=str(data.get("url") or ""),
        final_url=str(data.get("final_url") or ""),
        http_status=data.get("http_status"),
        html=str(data.get("html") or ""),
        markdown=str(data.get("markdown") or ""),
        source=source,  # type: ignore[arg-type]
    )


def _strip_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in ("negative", "expires_at")}


def _negative_result(url: str) -> PageFetchResult:
    from aperix_geo.services.crawl.types import PageFetchResult

    return PageFetchResult(url=url.strip(), source="none")


def _load_page_payload(payload: dict[str, Any]) -> PageFetchResult | str:
    if payload.get("negative"):
        return "negative"
    return _page_from_dict(_strip_meta(payload))


def _page_memory_get(logical: str) -> PageFetchResult | None | str:
    payload = _page_memory.get(logical)
    if payload is None:
        return None
    return _load_page_payload(payload)


def _hydrate_page_payload(logical: str, data: dict[str, Any], *, remaining: int) -> PageFetchResult | str:
    expires_at = int(data.get("expires_at") or (time.time() + remaining))
    if data.get("negative"):
        _page_memory.set(
            logical,
            {"negative": True, "expires_at": expires_at},
            expires_at=expires_at,
        )
        return "negative"
    plain = _unpack_redis_fields(_strip_meta(data))
    result = _page_from_dict(plain)
    payload = _page_to_dict(result)
    payload["expires_at"] = expires_at
    _page_memory.set(logical, payload, expires_at=expires_at)
    return result


def _hydrate_page_from_redis(logical: str) -> PageFetchResult | None | str:
    hit = redis_get_json_with_remaining_ttl(_page_redis_key(logical))
    if hit is None:
        return None
    return _hydrate_page_payload(logical, hit[0], remaining=hit[1])


def get_cached_page(
    url: str,
    *,
    max_chars: int,
    crawl_fallback: bool,
    ttl_s: int,
    negative_ttl_s: int = 0,
) -> PageFetchResult | None:
    """Return cached page, None on miss. Negative cache returns empty failed result."""
    if ttl_s <= 0 and negative_ttl_s <= 0:
        return None

    logical = _logical_key(url, max_chars=max_chars, crawl_fallback=crawl_fallback)

    mem = _page_memory_get(logical)
    if mem == "negative":
        return _negative_result(url)
    if mem is not None:
        return mem

    redis_hit = _hydrate_page_from_redis(logical)
    if redis_hit == "negative":
        return _negative_result(url)
    if redis_hit is not None:
        return redis_hit

    return None


def set_cached_page(
    url: str,
    result: PageFetchResult,
    *,
    max_chars: int,
    crawl_fallback: bool,
    ttl_s: int,
) -> None:
    if ttl_s <= 0 or not result.fetch_ok:
        return
    logical = _logical_key(url, max_chars=max_chars, crawl_fallback=crawl_fallback)
    expires_at = expires_at_from_ttl(ttl_s)
    payload = _page_to_dict(result)
    payload["expires_at"] = expires_at
    _page_memory.set(logical, payload, expires_at=expires_at)
    redis_set_json_exat(_page_redis_key(logical), _pack_redis_fields(payload), expires_at=expires_at)
    logger.debug("页面抓取缓存写入 %s", normalize_crawl_cache_url(url.strip()))


def set_negative_cached_page(
    url: str,
    *,
    max_chars: int,
    crawl_fallback: bool,
    negative_ttl_s: int,
) -> None:
    if negative_ttl_s <= 0:
        return
    logical = _logical_key(url, max_chars=max_chars, crawl_fallback=crawl_fallback)
    expires_at = expires_at_from_ttl(negative_ttl_s)
    payload = {"negative": True, "expires_at": expires_at}
    _page_memory.set(logical, payload, expires_at=expires_at)
    redis_set_json_exat(_page_redis_key(logical), payload, expires_at=expires_at)


def clear_page_cache() -> None:
    _page_memory.clear()


# --- DNS preflight cache ---

_DNS_L1_MAX = 2048
_dns_memory = BoundedTTLCache(_DNS_L1_MAX)
_DNS_REDIS_PREFIX = "aperix:dns:v1:"


def _dns_redis_key(host: str) -> str:
    digest = hashlib.sha256(host.strip().lower().encode("utf-8")).hexdigest()
    return f"{_DNS_REDIS_PREFIX}{digest}"


def _lookup_dns(host: str, *, timeout_s: float) -> bool:
    try:
        prev = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_s)
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            return True
        finally:
            socket.setdefaulttimeout(prev)
    except OSError:
        return False


def host_resolves_cached(host: str, *, timeout_s: float = 3.0, ttl_s: int = 0) -> bool:
    key = host.strip().lower()
    if not key:
        return False
    if ttl_s <= 0:
        return _lookup_dns(key, timeout_s=timeout_s)

    cached = _dns_memory.get(key)
    if cached is not None:
        return bool(cached)

    hit = redis_get_json_with_remaining_ttl(_dns_redis_key(key))
    if hit is not None:
        data, remaining = hit
        if "ok" in data:
            ok = bool(data["ok"])
            expires_at = int(data.get("expires_at") or (time.time() + remaining))
            _dns_memory.set(key, ok, expires_at=expires_at)
            return ok

    ok = _lookup_dns(key, timeout_s=timeout_s)
    expires_at = expires_at_from_ttl(ttl_s)
    _dns_memory.set(key, ok, expires_at=expires_at)
    redis_set_json_exat(_dns_redis_key(key), {"ok": ok, "expires_at": expires_at}, expires_at=expires_at)
    return ok


def clear_dns_cache() -> None:
    _dns_memory.clear()
