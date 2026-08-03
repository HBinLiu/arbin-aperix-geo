"""Domain normalization and homepage URL selection for favicon."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from aperix_geo.utils.net import (
    append_http_homepage_variants,
    explicit_http_url,
    favicon_from,
    homepage_url_candidates,
    is_valid_hostname,
    registrable_from,
)


class FaviconMode(str, Enum):
    """HOME: domain-list / apex homepage. PAGE: article or deep URL."""

    HOME = "home"
    PAGE = "page"


@dataclass(frozen=True, slots=True)
class FaviconRequest:
    """Normalized favicon lookup.

    - ``cache_key``: disk/mem key (``favicon_from`` — may keep meaningful subdomain)
    - ``apex``: eTLD+1 (``registrable_from``) for domain-list aliasing
    - ``fetch_url``: URL used only to drive network discovery
    - ``mode``: HOME allows negative cache + apex promote; PAGE does not
    """

    cache_key: str
    apex: str
    fetch_url: str
    mode: FaviconMode


def is_favicon_homepage_url(page_url: str, domain: str) -> bool:
    """True when *page_url* is a bare homepage for *domain* (cache_key)."""
    parsed = urlparse(page_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.query or parsed.fragment:
        return False
    return favicon_from(parsed.netloc) == domain


def normalize_favicon_request(raw: str) -> FaviconRequest | None:
    """Parse API/UI input into a single FaviconRequest."""
    fetch_url = explicit_http_url(raw)
    if not fetch_url:
        return None
    cache_key = favicon_from(fetch_url)
    if not cache_key or not is_valid_hostname(cache_key):
        return None
    apex = registrable_from(cache_key) or cache_key
    mode = FaviconMode.HOME if is_favicon_homepage_url(fetch_url, cache_key) else FaviconMode.PAGE
    return FaviconRequest(cache_key=cache_key, apex=apex, fetch_url=fetch_url, mode=mode)


def resolve_favicon_request_url(raw: str) -> tuple[str, str] | None:
    """Backward-compatible: ``(cache_key, fetch_url)``."""
    req = normalize_favicon_request(raw)
    if req is None:
        return None
    return req.cache_key, req.fetch_url


def favicon_homepage_urls(host: str) -> list[str]:
    """Homepage candidates for HOME-mode discovery (HTTPS first, HTTP fallback)."""
    host = host.strip().lower()
    if not host:
        return []
    root = registrable_from(host)
    key = favicon_from(host)
    if key and root and key != root:
        return append_http_homepage_variants([f"https://{key}/"])
    return homepage_url_candidates(root or host, prefer_www=False, include_http=True)
