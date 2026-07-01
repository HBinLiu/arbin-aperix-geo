"""Pydantic helpers for user-supplied HTTP(S) URLs.

Two layers (do not mix):

- ``validate_optional_http_url`` — **storage** (DB / session): empty ok; with scheme
  preserve http/https; bare host/path stored as-is (no forced scheme).
- ``parse_url`` (``utils.url``) — **fetch** (crawl / favicon / probe): always returns
  http(s); bare input defaults to ``http://``.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import HttpUrl, TypeAdapter, ValidationError

_HTTP_URL = TypeAdapter(HttpUrl)


def normalize_validated_http_url(value: object) -> str:
    """Validate with Pydantic HttpUrl; root URLs omit trailing slash."""
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = str(_HTTP_URL.validate_python(text))
    parsed = urlparse(normalized)
    if parsed.path in ("", "/") and not parsed.query and not parsed.fragment:
        return f"{parsed.scheme}://{parsed.netloc}"
    return normalized


def validate_optional_http_url(value: object) -> str:
    """Empty allowed; http(s) URL or bare host/path (不必 https 开头)。"""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""

    if re.match(r"^https?://", text, re.I):
        try:
            return normalize_validated_http_url(text)
        except ValidationError as exc:
            raise ValueError("Invalid HTTP URL") from exc

    from aperix_geo.utils.net import host_from, is_brand_domain

    bare = text.lstrip("/")
    host = host_from(bare)
    if not host or not is_brand_domain(host):
        raise ValueError("Invalid website URL or domain")
    return bare[:255]
