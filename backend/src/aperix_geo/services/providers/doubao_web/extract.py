"""Pure extraction helpers for Doubao Web panel text (unit-testable)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from aperix_geo.services.providers._helpers import dedupe_search_queries, dedupe_urls
from aperix_geo.services.providers.doubao_web.selectors import SEARCH_PANEL_FULL, SEARCH_PANEL_HINT

_QUOTE_RE = re.compile(
    r"[“「『\"]([^”」』\"]{1,200})[”」』\"]"
)
_URL_RE = re.compile(r"https?://[^\s<>\"'）】\]]+", re.IGNORECASE)
_SHARE_HOST_HINTS = ("doubao.com", "d.doubao.com", "www.doubao.com")


def extract_quoted_queries(panel_text: str) -> tuple[str, ...]:
    """Pull search keywords wrapped in quotes from the search panel body."""
    if not (panel_text or "").strip():
        return ()
    found = [m.group(1).strip() for m in _QUOTE_RE.finditer(panel_text) if m.group(1).strip()]
    return dedupe_search_queries(found)


def extract_urls(text: str) -> tuple[str, ...]:
    if not (text or "").strip():
        return ()
    raw = [_strip_url_trailing(m.group(0)) for m in _URL_RE.finditer(text)]
    return dedupe_urls(raw)


def panel_present(text: str) -> bool:
    return bool(SEARCH_PANEL_HINT.search(text or ""))


def panel_counts(text: str) -> tuple[int, int] | None:
    match = SEARCH_PANEL_FULL.search(text or "")
    if not match:
        return None
    return int(match.group("nq")), int(match.group("nr"))


def pick_share_url(candidates: list[str] | tuple[str, ...]) -> str:
    """Prefer doubao share hosts; otherwise first http(s) URL."""
    cleaned = [u.strip() for u in candidates if (u or "").strip().startswith("http")]
    if not cleaned:
        return ""
    for url in cleaned:
        host = (urlparse(url).hostname or "").lower()
        if any(hint in host for hint in _SHARE_HOST_HINTS) or "share" in url.lower():
            return url
    return cleaned[0]


def _strip_url_trailing(url: str) -> str:
    return url.rstrip(".,;:!?，。；：、")
