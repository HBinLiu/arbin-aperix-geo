"""Main-content extraction via official ``rs-trafilatura`` (optional)."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.url_type.taxonomy import DEFAULT_URL_TYPE, normalize_url_type

logger = logging.getLogger(__name__)


def _coerce_page_type(raw: Any) -> str:
    if raw is None:
        return DEFAULT_URL_TYPE
    if isinstance(raw, tuple) and raw:
        raw = raw[0]
    text = str(raw).strip()
    if "." in text and not text.startswith("http"):
        text = text.rsplit(".", 1)[-1]
    return normalize_url_type(text)


def _text_from_extract_result(result: Any) -> str:
    if result is None:
        return ""
    for attr in ("text", "content", "main_text", "content_markdown"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(result, dict):
        for key in ("text", "content", "main_text", "content_markdown"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(result, str):
        return result.strip()
    return ""


def _page_type_from_extract_result(result: Any) -> str:
    page_type = getattr(result, "page_type", None)
    if page_type is None and isinstance(result, dict):
        page_type = result.get("page_type")
    if page_type is None:
        return ""
    return _coerce_page_type(page_type)


def extract_main_content(html: str, *, url: str = "") -> tuple[str, str]:
    """Extract main body text and page type from HTML.

    Returns ``(body_text, url_type)``. Empty body means unavailable (caller
    should keep the legacy markdown/HTML path). Missing package or errors
    also return empty body — no config switch.
    """
    html_text = (html or "").strip()
    if not html_text:
        return "", ""

    try:
        import rs_trafilatura  # type: ignore[import-not-found]
    except Exception:
        return "", ""

    raw_url = (url or "").strip() or None
    try:
        result = rs_trafilatura.extract(html_text, url=raw_url)
    except Exception:
        logger.warning("rs_trafilatura.extract failed url=%s", raw_url or "", exc_info=True)
        return "", ""

    body = _text_from_extract_result(result)
    page_type = _page_type_from_extract_result(result)
    return body, page_type
