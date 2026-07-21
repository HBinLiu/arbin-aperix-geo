"""URL / page-type classification via official ``rs-trafilatura``."""

from __future__ import annotations

import logging

from aperix_geo.services.url_type.extract import (
    _coerce_page_type,
    extract_main_content,
)
from aperix_geo.services.url_type.taxonomy import DEFAULT_URL_TYPE

logger = logging.getLogger(__name__)


def classify_url(url: str) -> str:
    """Classify page type from URL using ``rs_trafilatura.classify_url``.

    Returns an English code (article/forum/...). Uses ``other`` when the
    package is missing or classification fails — Chinese labels stay on the frontend.
    """
    raw_url = (url or "").strip()
    if not raw_url:
        return DEFAULT_URL_TYPE

    try:
        import rs_trafilatura  # type: ignore[import-not-found]
    except Exception:
        logger.debug("rs-trafilatura not installed; url_type=other")
        return DEFAULT_URL_TYPE

    try:
        result = rs_trafilatura.classify_url(raw_url)
    except Exception:
        logger.warning("rs_trafilatura.classify_url failed url=%s", raw_url, exc_info=True)
        return DEFAULT_URL_TYPE

    return _coerce_page_type(result)


def classify_url_type(url: str) -> str:
    """Alias for :func:`classify_url`."""
    return classify_url(url)


def classify_page_type(url: str, *, html: str = "", title: str = "") -> str:
    """Prefer extract page_type when HTML is available; else URL-only classify."""
    _ = title
    raw_url = (url or "").strip()
    html_text = (html or "").strip()
    if html_text:
        _body, page_type = extract_main_content(html_text, url=raw_url)
        if page_type:
            return page_type
    return classify_url(raw_url)
