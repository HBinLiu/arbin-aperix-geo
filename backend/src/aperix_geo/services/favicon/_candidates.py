"""Build ordered favicon URL candidate lists."""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import urljoin, urlparse

from aperix_geo.services.favicon._domain import favicon_homepage_urls
from aperix_geo.services.favicon._parse import (
    dedupe_urls,
    page_icon_candidates_from_html,
    subdomain_favicon_candidates_from_html,
)
from aperix_geo.utils.net import explicit_http_url

_MAX_PAGE_HTML_CHARS = 400_000
_HEADLESS_MIN_TIMEOUT_S = 8.0

_STANDARD_ICON_PATHS = (
    "/favicon.ico",
    "/favicon.png",
    "/favicon.svg",
    "/assets/favicon.ico",
    "/static/favicon.ico",
    "/apple-touch-icon.png",
)
_CDN_HOST_PREFIXES = ("static", "cdn", "img", "assets")
_QUICK_FAVICON_PATHS = ("/favicon.ico", "/favicon.png", "/apple-touch-icon.png")


def standard_path_urls_for_page(page_url: str) -> list[str]:
    """给定完整页面 URL，仅在同 origin 上尝试常见 favicon 路径。"""
    parsed = urlparse(page_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return []
    base = f"{parsed.scheme}://{parsed.netloc}/"
    return dedupe_urls(urljoin(base, path) for path in _QUICK_FAVICON_PATHS)


def _urls_for_homes(domain: str, paths: tuple[str, ...]) -> list[str]:
    urls: list[str] = []
    for home in favicon_homepage_urls(domain):
        for path in paths:
            urls.append(urljoin(home, path))
    return urls


def main_standard_path_urls(domain: str) -> list[str]:
    """Static icon paths on the site's own homepage hosts (www + apex)."""
    return dedupe_urls(_urls_for_homes(domain, _STANDARD_ICON_PATHS))


def cdn_prefix_standard_path_urls(domain: str) -> list[str]:
    """Static icon paths on common CDN-style subdomains (lowest priority)."""
    urls: list[str] = []
    for prefix in _CDN_HOST_PREFIXES:
        base = f"https://{prefix}.{domain}/"
        for path in _QUICK_FAVICON_PATHS:
            urls.append(urljoin(base, path))
    return dedupe_urls(urls)


class _HomepageHtmlSources:
    """Fetch homepage HTML once per source and derive page vs subdomain icon lists."""

    def __init__(self, domain: str, *, timeout_s: float) -> None:
        self.domain = domain
        self.timeout_s = timeout_s
        self._fetch_pages: list[tuple[str, str]] | None = None
        self._crawl_pages: list[tuple[str, str]] | None = None

    def _slice_html(self, html: str) -> str:
        return html[:_MAX_PAGE_HTML_CHARS]

    def _load_fetch_pages(self) -> list[tuple[str, str]]:
        if self._fetch_pages is not None:
            return self._fetch_pages

        from aperix_geo.services.crawl import fetch_page, page_crawl_settings

        crawl = replace(page_crawl_settings(), crawl_fallback=False)
        pages: list[tuple[str, str]] = []
        for home in favicon_homepage_urls(self.domain):
            result = fetch_page(home, crawl=crawl, max_chars=_MAX_PAGE_HTML_CHARS)
            if result.html.strip():
                pages.append((result.final_url or home, result.html))
        self._fetch_pages = pages
        return pages

    def _load_crawl_pages(self) -> list[tuple[str, str]]:
        if self._crawl_pages is not None:
            return self._crawl_pages

        from aperix_geo.services.crawl._crawl4ai import fetch_url_crawl4ai
        from aperix_geo.services.crawl.settings import page_crawl_settings

        crawl = page_crawl_settings()
        pages: list[tuple[str, str]] = []
        if not crawl.crawl_fallback:
            self._crawl_pages = pages
            return pages

        wait_s = max(self.timeout_s, crawl.crawl_timeout_s, _HEADLESS_MIN_TIMEOUT_S)
        for home in favicon_homepage_urls(self.domain):
            final_url, html, _markdown, source = fetch_url_crawl4ai(
                home,
                timeout_s=wait_s,
                max_chars=_MAX_PAGE_HTML_CHARS,
                max_concurrent=crawl.crawl4ai_concurrency,
            )
            if source == "none" or not html.strip():
                continue
            pages.append((final_url or home, html))
        self._crawl_pages = pages
        return pages

    def _first_page_icons(self, pages: list[tuple[str, str]]) -> list[str]:
        for page_url, html in pages:
            if urls := page_icon_candidates_from_html(self._slice_html(html), page_url):
                return urls
        return []

    def _first_subdomain_icons(self, pages: list[tuple[str, str]]) -> list[str]:
        for _page_url, html in pages:
            if urls := subdomain_favicon_candidates_from_html(self._slice_html(html), self.domain):
                return urls
        return []

    def page_icons_from_fetch(self) -> list[str]:
        return self._first_page_icons(self._load_fetch_pages())

    def subdomain_icons_from_fetch(self) -> list[str]:
        return self._first_subdomain_icons(self._load_fetch_pages())

    def page_icons_from_crawl4ai(self) -> list[str]:
        return self._first_page_icons(self._load_crawl_pages())

    def subdomain_icons_from_crawl4ai(self) -> list[str]:
        return self._first_subdomain_icons(self._load_crawl_pages())


def icons_from_page_url(page_url: str, *, timeout_s: float) -> list[str]:
    """Parse icon URLs from a specific page (e.g. citation URL)."""
    page_url = page_url.strip()
    if not page_url:
        return []

    from aperix_geo.services.crawl import fetch_page, page_crawl_settings

    crawl = replace(page_crawl_settings(), crawl_fallback=False)
    result = fetch_page(page_url, crawl=crawl, max_chars=_MAX_PAGE_HTML_CHARS)
    if not result.html.strip():
        return []
    return page_icon_candidates_from_html(
        result.html[:_MAX_PAGE_HTML_CHARS],
        result.final_url or page_url,
    )


def discover_icon_url_batches(
    domain: str,
    *,
    timeout_s: float,
    page_url: str | None = None,
) -> list[list[str]]:
    """Return icon URL batches in fetch priority order."""
    wait_s = max(timeout_s, _HEADLESS_MIN_TIMEOUT_S)
    explicit = explicit_http_url(page_url.strip()) if page_url and page_url.strip() else ""
    if explicit:
        return [
            icons_from_page_url(explicit, timeout_s=wait_s),
            standard_path_urls_for_page(explicit),
        ]

    src = _HomepageHtmlSources(domain, timeout_s=wait_s)
    return [
        src.page_icons_from_fetch(),
        src.page_icons_from_crawl4ai(),
        main_standard_path_urls(domain),
        src.subdomain_icons_from_fetch(),
        src.subdomain_icons_from_crawl4ai(),
        cdn_prefix_standard_path_urls(domain),
    ]
