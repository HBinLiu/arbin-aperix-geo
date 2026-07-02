"""Domain normalization and homepage URL selection."""

from __future__ import annotations

from urllib.parse import urlparse

from aperix_geo.utils.net import (
    append_http_homepage_variants,
    explicit_http_url,
    favicon_from,
    homepage_url_candidates,
    is_valid_hostname,
    registrable_from,
)


def resolve_favicon_request_url(raw: str) -> tuple[str, str] | None:
    """将 API ``url`` 参数解析为 (favicon_cache_key, fetchable_page_url)。"""
    page_url = explicit_http_url(raw)
    if not page_url:
        return None
    domain = favicon_from(page_url)
    if not domain or not is_valid_hostname(domain):
        return None
    return domain, page_url


def is_favicon_homepage_url(page_url: str, domain: str) -> bool:
    """是否为站点首页 URL（用于 negative cache 与仅域名请求等价）。"""
    parsed = urlparse(page_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.query or parsed.fragment:
        return False
    return favicon_from(parsed.netloc) == domain


def favicon_homepage_urls(host: str) -> list[str]:
    """favicon 抓取用的首页候选（裸域优先，HTTPS 后 HTTP 兜底）。"""
    host = host.strip().lower()
    if not host:
        return []
    root = registrable_from(host)
    key = favicon_from(host)
    if key and root and key != root:
        return append_http_homepage_variants([f"https://{key}/"])
    return homepage_url_candidates(root or host, prefer_www=False, include_http=True)
