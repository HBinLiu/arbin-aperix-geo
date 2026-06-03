"""URL extraction, hostname normalization, and DNS helpers."""

from __future__ import annotations

import re
import socket
from urllib.parse import urlparse, urlunparse

import httpx

from aperix_geo.utils.domains import registrable_domain, strip_hostname
from aperix_geo.utils.http import HTML_FETCH_HEADERS

_URL_RE = re.compile(r"https?://[^\s\)\]\"']+", re.IGNORECASE)
_STRIP_WWW = re.compile(r"^www\.", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(_URL_RE.findall(text or "")))


def hostname_from_url(url: str) -> str | None:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = (parsed.netloc or "").lower().split(":")[0]
    if not host:
        return None
    host = _STRIP_WWW.sub("", host)
    return host or None


def normalize_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    host = strip_hostname(domain)
    return host or None


def host_matches_root(host: str | None, root: str | None) -> bool:
    if not host or not root:
        return False
    h = host.lower().replace("www.", "")
    return h == root or h.endswith(f".{root}")


def normalize_page_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", parsed.query, ""))


def host_resolves(host: str, *, timeout_s: float = 3.0) -> bool:
    try:
        prev = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_s)
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            return True
        finally:
            socket.setdefaulttimeout(prev)
    except OSError:
        return False


def homepage_urls(domain: str) -> list[str]:
    """
    候选首页 URL（仅 HTTPS，优先 www）。

    部分站点（如 shushangyun.com）裸域 http:// 会在 80 端口返回
    「plain HTTP request was sent to HTTPS port」，必须用 https:// 且常需 www。
    """
    root = registrable_domain(domain)
    if not root:
        return []

    hosts: list[str] = []
    if host_resolves(f"www.{root}"):
        hosts.append(f"www.{root}")
    if host_resolves(root) and root not in hosts:
        hosts.append(root)
    if not hosts:
        hosts = [root]

    return [f"https://{h}/" for h in hosts]


def root_website_url(url: str) -> str:
    """保留 scheme + host，去掉 path/query/fragment 与末尾斜杠。"""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    host = parsed.netloc.lower().split(":")[0]
    return f"{parsed.scheme.lower()}://{host}"


def fallback_website_url(domain: str) -> str:
    """无网络探测时的默认首页 URL（优先 www + HTTPS）。"""
    root = registrable_domain(domain)
    if not root:
        return ""
    if host_resolves(f"www.{root}"):
        return f"https://www.{root}"
    return f"https://{root}"


def _website_url_candidates(domain: str) -> list[str]:
    root = registrable_domain(domain)
    if not root:
        return []
    hosts: list[str] = []
    if host_resolves(f"www.{root}"):
        hosts.append(f"www.{root}")
    if root not in hosts:
        hosts.append(root)
    if not hosts:
        hosts = [root]
    urls: list[str] = []
    for host in hosts:
        for scheme in ("https", "http"):
            urls.append(f"{scheme}://{host}")
    return urls


def _probe_reachable_root_url(url: str, *, timeout_s: float, client: httpx.Client) -> str | None:
    try:
        resp = client.get(url, follow_redirects=True, timeout=timeout_s)
        if resp.status_code < 400:
            return root_website_url(str(resp.url))
    except httpx.HTTPError:
        return None
    return None


def resolve_website_url(raw: str, *, timeout_s: float = 5.0, probe: bool = True) -> tuple[str, str]:
    """
    从用户输入解析 (registrable_domain, website_url)。

    website_url 为可访问的首页根链接；probe=True 时会依次尝试 https/http。
    """
    domain = registrable_domain(raw)
    if not domain:
        return "", ""

    if probe:
        try:
            with httpx.Client(headers=HTML_FETCH_HEADERS, follow_redirects=True) as client:
                for candidate in _website_url_candidates(domain):
                    resolved = _probe_reachable_root_url(candidate, timeout_s=timeout_s, client=client)
                    if resolved:
                        return domain, resolved
        except OSError:
            pass

    return domain, fallback_website_url(domain)
