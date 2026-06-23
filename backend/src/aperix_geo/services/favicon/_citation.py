"""Persist favicon from citation page HTML (no extra page fetch)."""

from __future__ import annotations

import logging
import threading

from aperix_geo.config import get_settings
from aperix_geo.services.crawl._httpx import get_icon_httpx_client
from aperix_geo.utils.net import favicon_from
from aperix_geo.services.favicon._fetch import fetch_first_icon
from aperix_geo.services.favicon._parse import page_icon_candidates_from_html
from aperix_geo.services.favicon._storage import read_cached_favicon, static_favicon_path

logger = logging.getLogger(__name__)

_MAX_HTML_CHARS = 400_000
_DEFAULT_TIMEOUT_S = 5.0


def favicon_cached_for_domain(domain: str) -> bool:
    if read_cached_favicon(domain):
        return True
    return static_favicon_path(domain) is not None


def maybe_cache_favicon_from_page_html(
    *,
    page_url: str,
    html: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> bool:
    """Try to persist domain favicon using HTML already fetched for citation metadata."""
    page_url = page_url.strip()
    if not page_url or not html.strip():
        return False

    domain = favicon_from(page_url)
    if not domain or favicon_cached_for_domain(domain):
        return False

    candidates = page_icon_candidates_from_html(html[:_MAX_HTML_CHARS], page_url)
    if not candidates:
        return False

    client = get_icon_httpx_client()
    if fetch_first_icon(client, domain, candidates, timeout_s=timeout_s) is None:
        return False

    logger.debug("引用页顺带缓存 favicon domain=%s page=%s", domain, page_url)
    return True


def schedule_citation_favicon_from_page_html(
    *,
    page_url: str,
    html: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> None:
    """Cache favicon off the citation fetch hot path (daemon thread)."""
    page_url = page_url.strip()
    html_copy = html[:_MAX_HTML_CHARS]
    if not page_url or not html_copy.strip():
        return

    def _run() -> None:
        try:
            maybe_cache_favicon_from_page_html(
                page_url=page_url,
                html=html_copy,
                timeout_s=timeout_s,
            )
        except Exception:
            logger.warning("引用页后台 favicon 缓存失败 page=%s", page_url, exc_info=True)

    threading.Thread(target=_run, name="citation-favicon", daemon=True).start()


def cache_citation_favicon_from_page_html(
    *,
    page_url: str,
    html: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> None:
    """Inline or background favicon cache depending on ``citation_favicon_inline``."""
    if get_settings().citation_favicon_inline:
        maybe_cache_favicon_from_page_html(
            page_url=page_url,
            html=html,
            timeout_s=timeout_s,
        )
        return
    schedule_citation_favicon_from_page_html(
        page_url=page_url,
        html=html,
        timeout_s=timeout_s,
    )
