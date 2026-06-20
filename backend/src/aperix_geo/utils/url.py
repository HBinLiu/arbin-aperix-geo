"""URL extraction, hostname normalization, and DNS helpers."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from aperix_geo.utils.domains import is_valid_hostname, registrable_domain, strip_hostname
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
_NUMERIC_ONLY_HOST_RE = re.compile(r"^[\d.]+$")


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


def is_valid_citation_host(host: str | None) -> bool:
    """Real citation host: not placeholder, not numeric-only (e.g. 9.8), has a letter TLD/label."""
    h = strip_hostname(host or "")
    if not h or is_placeholder_citation_host(h):
        return False
    if _NUMERIC_ONLY_HOST_RE.fullmatch(h):
        return False
    if not re.search(r"[a-z]", h):
        return False
    return is_valid_hostname(h)


def filter_citation_urls(urls: list[str]) -> list[str]:
    """去重并剔除占位/无效域名的引用 URL。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        key = str(raw).strip()
        if not key or key in seen:
            continue
        host = hostname_from_url(key)
        if not host or not is_valid_citation_host(host):
            continue
        seen.add(key)
        out.append(key)
    return out


def is_llm_numeric_fake_url(url: str) -> bool:
    """True when http(s) URL host looks like an LLM footnote score (e.g. 9.8, 0.5, 3.0.0.1)."""
    key = (url or "").strip()
    if not key.lower().startswith(("http://", "https://")):
        return False
    host = hostname_from_url(key)
    if not host:
        return True
    if _NUMERIC_ONLY_HOST_RE.fullmatch(host):
        return True
    return not re.search(r"[a-z]", host)


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


def _homepage_https_urls(domain: str, *, prefer_www: bool) -> list[str]:
    """
    候选首页 URL（仅 HTTPS）。

    prefer_www=True：www 优先（竞品 head 抓取等）。
    prefer_www=False：裸域优先（画像回退、favicon 等）。
    """
    root = registrable_domain(domain)
    if not root:
        return []

    www = f"www.{root}"
    hosts: list[str] = []
    if prefer_www:
        if host_resolves(www):
            hosts.append(www)
        if host_resolves(root) and root not in hosts:
            hosts.append(root)
    else:
        if host_resolves(root):
            hosts.append(root)
        if host_resolves(www) and www not in hosts:
            hosts.append(www)
    if not hosts:
        hosts = [root]

    return [f"https://{h}/" for h in hosts]


def homepage_urls(domain: str) -> list[str]:
    """
    候选首页 URL（仅 HTTPS，优先 www）。

    部分站点（如 shushangyun.com）裸域 http:// 会在 80 端口返回
    「plain HTTP request was sent to HTTPS port」，必须用 https:// 且常需 www。
    """
    return _homepage_https_urls(domain, prefer_www=True)


def candidate_website_urls(domain: str, *, preferred_url: str = "") -> list[str]:
    """URL 候选：优先给定链接，再试 domain 的 www/裸域首页。"""
    seen: set[str] = set()
    out: list[str] = []
    preferred = normalize_user_website_input(preferred_url)
    if preferred and preferred not in seen:
        seen.add(preferred)
        out.append(preferred)
    for url in homepage_urls(domain):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def probe_first_reachable_url(
    urls: list[str],
    *,
    timeout_s: float = 5.0,
) -> str | None:
    """轻量可达性探测：httpx GET，status<400 即视为可打开（不用 Crawl4AI）。"""
    from aperix_geo.utils.http import HTML_FETCH_HEADERS

    candidates: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        url = normalize_user_website_input(raw)
        if url and url not in seen:
            seen.add(url)
            candidates.append(url)
    if not candidates:
        return None

    try:
        with httpx.Client(headers=HTML_FETCH_HEADERS, follow_redirects=True) as client:
            for url in candidates:
                resolved = _probe_reachable_root_url(url, timeout_s=timeout_s, client=client)
                if resolved:
                    return resolved
    except OSError:
        return None
    return None


def homepage_urls_apex_first(domain: str) -> list[str]:
    """
    候选首页 URL（仅 HTTPS，裸域优先，再试 www）。

    用于 profile 抓取回退、favicon 等；Setup 首页优先走 profile_homepage_crawl_urls。
    """
    return _homepage_https_urls(domain, prefer_www=False)


def normalize_user_website_input(raw: str) -> str:
    """将用户输入转为可抓取的 http(s) URL，保留 host 与 path。"""
    s = raw.strip()
    if not s:
        return ""
    if re.match(r"^https?://", s, re.I):
        return s
    return f"https://{s.lstrip('/')}"


def profile_homepage_crawl_urls(raw_input: str, *, root: str) -> list[str]:
    """
    Setup 画像首页抓取顺序：用户输入的完整 URL 优先，失败后再试 apex/www 候选。
    """
    urls: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = u.strip()
        if not u or u in seen:
            return
        seen.add(u)
        urls.append(u)

    user = normalize_user_website_input(raw_input)
    if user:
        add(user)
        parsed = urlparse(user)
        if parsed.scheme and parsed.netloc and parsed.path in ("", "/"):
            add(f"{parsed.scheme}://{parsed.netloc}/")

    if root:
        for u in homepage_urls_apex_first(root):
            add(u)
    return urls


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
