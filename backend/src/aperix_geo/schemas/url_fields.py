"""Pydantic helpers for user-supplied HTTP(S) URLs."""

from __future__ import annotations

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
    """Empty string allowed; non-empty must be a valid http(s) URL."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        return normalize_validated_http_url(text)
    except ValidationError as exc:
        raise ValueError("Invalid HTTP URL") from exc
