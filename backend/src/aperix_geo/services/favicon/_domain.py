"""Domain normalization and homepage URL selection."""

from __future__ import annotations

from urllib.parse import urlparse

from aperix_geo.utils.net import (
    apex_homepage_urls,
    favicon_from,
    is_valid_hostname,
    parse_url,
    registrable_from,
)


def resolve_favicon_request_url(raw: str) -> tuple[str, str] | None:
    """将 API ``url`` 参数解析为 (domain, page_url)。"""
    page_url = parse_url(raw)
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
    """favicon 抓取用的首页候选。"""
    host = host.strip().lower()
    if not host:
        return []
    root = registrable_from(host)
    key = favicon_from(host)
    if key and root and key != root:
        return [f"https://{key}/"]
    return apex_homepage_urls(root or host) or [f"https://{host}/"]
