"""Embed favicons in brand reports as data URLs (works in iframe preview + PDF)."""

from __future__ import annotations

import base64

from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced
from aperix_geo.services.favicon._storage import read_cached_favicon
from aperix_geo.utils.net import favicon_from


def favicon_data_url(domain: str | None, *, timeout_s: float = 4.0) -> str | None:
    """Resolve favicon for *domain* and return a ``data:`` URI, or ``None``."""
    key = favicon_from(domain)
    if not key:
        return None

    cached = read_cached_favicon(key)
    if cached is None:
        # Homepage URL → HOME mode (wide discovery + negative cache + apex promote).
        cached = resolve_favicon_coalesced(
            key,
            page_url=f"https://{key}/",
            timeout_s=timeout_s,
        )
    if cached is None:
        return None

    body, media_type = cached
    encoded = base64.b64encode(body).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
