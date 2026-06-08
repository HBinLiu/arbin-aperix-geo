"""URL extraction, hostname normalization, and DNS helpers."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from aperix_geo.utils.domains import registrable_domain, strip_hostname
from aperix_geo.utils.http import HTML_FETCH_HEADERS

_URL_RE = re.compile(r"https?://[^\s\)\]\"']+", re.IGNORECASE)
_STRIP_WWW = re.compile(r"^www\.", re.IGNORECASE)

# RFC 2606 等保留/示例域，LLM 常当作占位 URL 输出，不应进入引用来源
_PLACEHOLDER_REGISTRABLE = frozenset(
    {
        "example.com",
        "example.net",
        "example.org",
        "example.edu",
        "example.gov",
        "test",
        "invalid",
        "localhost",
    },
)
_PLACEHOLDER_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(_URL_RE.findall(text or "")))


def is_placeholder_citation_host(host: str | None) -> bool:
    """示例/保留域名，不应计入引用来源。"""
    h = strip_hostname(host or "")
    if not h:
        return True
    if h in _PLACEHOLDER_HOSTS:
        return True
    root = registrable_domain(h)
    if root in _PLACEHOLDER_REGISTRABLE:
        return True
    return root.endswith((".example", ".test", ".localhost", ".invalid"))


def filter_citation_urls(urls: list[str]) -> list[str]:
    """去重并剔除占位/无效域名的引用 URL。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        key = str(raw).strip()
        if not key or key in seen:
            continue
        host = hostname_from_url(key)
        if not host or is_placeholder_citation_host(host):
            continue
        seen.add(key)
        out.append(key)
    return out


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


_TRACKING_QUERY_KEYS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "spm"})


def normalize_crawl_cache_url(url: str) -> str:
    """Normalize URL for crawl cache keys (host/path/query cleanup)."""
    raw = url.strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return raw
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _TRACKING_QUERY_KEYS or lowered.startswith("utm_"):
            continue
        query_pairs.append((key, value))
    query = urlencode(query_pairs)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))


def host_resolves(host: str, *, timeout_s: float = 3.0) -> bool:
    from aperix_geo.services.crawl._cache import _lookup_dns, host_resolves_cached
    from aperix_geo.services.crawl.settings import page_crawl_settings

    ttl_s = page_crawl_settings().dns_cache_ttl_s
    if ttl_s <= 0:
        return _lookup_dns(host, timeout_s=timeout_s)

    return host_resolves_cached(host, timeout_s=timeout_s, ttl_s=ttl_s)


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
