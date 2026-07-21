"""Page URL type taxonomy (aligned with web-page-classifier / rs-trafilatura).

English codes are stored in DB; Chinese labels live on the frontend.
"""

from __future__ import annotations

URL_TYPES: frozenset[str] = frozenset(
    {
        "article",
        "collection",
        "documentation",
        "forum",
        "listing",
        "product",
        "service",
        "other",
    }
)

DEFAULT_URL_TYPE = "other"


def normalize_url_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    if not key:
        return DEFAULT_URL_TYPE
    if key in {"category", "collection"}:
        return "collection"
    if key in {"docs", "documentation"}:
        return "documentation"
    return key if key in URL_TYPES else DEFAULT_URL_TYPE
