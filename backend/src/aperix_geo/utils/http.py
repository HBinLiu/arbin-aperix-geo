"""Shared HTTP client headers."""

from __future__ import annotations

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_ACCEPT_LANGUAGE = "zh-CN,zh;q=0.9"


def browser_headers(*, accept: str | None = None, **extra: str) -> dict[str, str]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Language": DEFAULT_ACCEPT_LANGUAGE,
    }
    if accept:
        headers["Accept"] = accept
    headers.update(extra)
    return headers


BROWSER_HEADERS = browser_headers()
HTML_FETCH_HEADERS = browser_headers(accept="text/html,application/xhtml+xml")
HTML_PAGE_FETCH_HEADERS = browser_headers(
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
)
ICON_FETCH_HEADERS = browser_headers(
    accept="image/avif,image/webp,image/apng,image/*,*/*;q=0.8,text/html;q=0.5",
)
