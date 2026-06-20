"""Domain normalization and homepage URL selection."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from aperix_geo.utils.domains import is_valid_hostname, registrable_domain, strip_hostname
from aperix_geo.utils.url import homepage_urls_apex_first


def normalize_favicon_domain(raw: str) -> str:
    """
    归一 favicon 主机名：去 www / 端口；gov 等子站保留完整主机名（如 yjj.gxzf.gov.cn）。

    主域（wise.com）仍归一为 eTLD+1；多一级子域不折叠到父域，避免抓错 favicon。
    """
    host = strip_hostname(raw).split(":")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    root = registrable_domain(host)
    if root and host != root and host.endswith(f".{root}"):
        return host
    return root or host


def resolve_favicon_request_url(raw: str) -> tuple[str, str] | None:
    """将 API ``url`` 参数解析为 (domain, page_url)。

    - ``page_url``：按该 URL 抓取 favicon（link/meta、子路径页等）。
    - ``domain``：内存 / 磁盘 / negative cache 的键（``{storage}/{domain}/``），不是 URL path。
    """
    s = raw.strip()
    if not s:
        return None
    if re.match(r"^https?://", s, re.I):
        page_url = s
    elif "/" in s:
        page_url = f"https://{s.lstrip('/')}"
    else:
        page_url = f"https://{s.lstrip('/')}/"

    domain = normalize_favicon_domain(page_url)
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
    return normalize_favicon_domain(parsed.netloc) == domain


def favicon_homepage_urls(host: str) -> list[str]:
    """favicon 抓取用的首页候选。

    - 子域（gov 子站、shop.foo.com）只请求自身主机。
    - 裸域（example.com，无 www 前缀）优先 apex，再试 www。
    """
    host = host.strip().lower()
    if not host:
        return []
    root = registrable_domain(host)
    if root and host != root and host.endswith(f".{root}"):
        return [f"https://{host}/"]

    return homepage_urls_apex_first(root or host) or [f"https://{host}/"]
