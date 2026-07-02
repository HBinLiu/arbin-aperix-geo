"""URL extraction, hostname normalization, and DNS helpers."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from aperix_geo.utils.domains import is_brand_domain, registrable_domain, registrable_from, strip_hostname
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


def is_citation_host(host: str | None) -> bool:
    """Real citation host: plausible domain and not a placeholder."""
    h = strip_hostname(host or "")
    if not h or is_placeholder_citation_host(h):
        return False
    return is_brand_domain(h)


def filter_citation_urls(urls: list[str]) -> list[str]:
    """去重并剔除占位/无效域名的引用 URL。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        key = str(raw).strip()
        if not key or key in seen:
            continue
        host = host_from_url(key)
        if not host or not is_citation_host(host):
            continue
        seen.add(key)
        out.append(key)
    return out


def is_llm_numeric_fake_url(url: str) -> bool:
    """True when http(s) URL host looks like an LLM footnote score (e.g. 9.8, 0.5, 3.0.0.1)."""
    key = (url or "").strip()
    if not key.lower().startswith(("http://", "https://")):
        return False
    host = host_from_url(key)
    if not host:
        return True
    if _NUMERIC_ONLY_HOST_RE.fullmatch(host):
        return True
    return not re.search(r"[a-z]", host)


def host_from_url(url: str) -> str | None:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = (parsed.netloc or "").lower().split(":")[0]
    if not host:
        return None
    host = _STRIP_WWW.sub("", host)
    return host or None


def citation_registrable_key(value: str) -> str:
    """Normalize URL/hostname input to ``tb_citation_domains.domain`` key (eTLD+1)."""
    text = (value or "").strip()
    if not text:
        return ""
    if "://" in text or text.startswith("//"):
        raw = text if not text.startswith("//") else f"https:{text}"
        return registrable_from(raw) or ""
    if "/" in text and "." in text.split("/", 1)[0]:
        return registrable_from(f"https://{text}") or ""
    root = registrable_from(text) or registrable_from(f"https://{text}")
    return root.lower() if root else text.split("/", 1)[0].lower()


def host_under_root(host: str | None, root: str | None) -> bool:
    if not host or not root:
        return False
    h = host.lower().replace("www.", "")
    return h == root or h.endswith(f".{root}")


def page_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", parsed.query, ""))


_TRACKING_QUERY_KEYS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "spm", "utm"})


def crawl_cache_url(url: str) -> str:
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


def host_resolves(host: str, *, timeout_s: float | None = None) -> bool:
    from aperix_geo.utils.dns import host_has_dns_records

    return host_has_dns_records(host, timeout_s=timeout_s)


def host_resolves_public(host: str, *, timeout_s: float | None = None) -> bool:
    """True when DNS resolves and every A/AAAA address is a public routable IP."""
    from aperix_geo.utils.dns import host_resolves_public as dns_host_resolves_public

    key = (host or "").strip().lower()
    if not key:
        return False
    return dns_host_resolves_public(key, timeout_s=timeout_s)


def _homepage_hosts(domain: str, *, prefer_www: bool) -> list[str]:
    """
    候选首页主机名（www / 裸域）。

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
    return hosts


def _homepage_scheme_urls(domain: str, *, prefer_www: bool, scheme: str) -> list[str]:
    return [f"{scheme}://{h}/" for h in _homepage_hosts(domain, prefer_www=prefer_www)]


def append_http_homepage_variants(urls: list[str]) -> list[str]:
    """在 HTTPS 首页候选后追加同 host 的 HTTP 变体（去重保序）。"""
    seen = set(urls)
    out = list(urls)
    for url in urls:
        if not url.startswith("https://"):
            continue
        http_url = f"http://{url[8:]}"
        if http_url not in seen:
            seen.add(http_url)
            out.append(http_url)
    return out


def homepage_url_candidates(
    domain: str,
    *,
    prefer_www: bool = True,
    include_http: bool = False,
) -> list[str]:
    """有序首页 URL 候选（HTTPS www/裸域；可选 HTTP 兜底）。"""
    urls = _homepage_scheme_urls(domain, prefer_www=prefer_www, scheme="https")
    if include_http:
        return append_http_homepage_variants(urls)
    return urls


def _homepage_https_urls(domain: str, *, prefer_www: bool) -> list[str]:
    """候选首页 URL（仅 HTTPS）。"""
    return homepage_url_candidates(domain, prefer_www=prefer_www, include_http=False)


def homepage_urls(domain: str) -> list[str]:
    """
    候选首页 URL（仅 HTTPS，优先 www）。

    部分站点（如 shushangyun.com）裸域 http:// 会在 80 端口返回
    「plain HTTP request was sent to HTTPS port」，必须用 https:// 且常需 www。
    """
    return _homepage_https_urls(domain, prefer_www=True)


def apex_homepage_urls(domain: str) -> list[str]:
    """候选首页 URL（仅 HTTPS，裸域优先，再试 www）。"""
    return _homepage_https_urls(domain, prefer_www=False)


def website_candidates(domain: str, *, preferred_url: str = "") -> list[str]:
    """URL 候选：优先给定链接，再试 HTTPS www/裸域，最后试 HTTP（部分站点仅开 80 端口）。"""
    seen: set[str] = set()
    out: list[str] = []
    preferred = parse_url(preferred_url)
    if preferred and preferred not in seen:
        seen.add(preferred)
        out.append(preferred)
    for url in homepage_url_candidates(domain, prefer_www=True, include_http=True):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def parse_url(raw: str) -> str:
    """Validate user URL input and return a fetchable http(s) URL (preserves scheme; bare defaults to http)."""
    from pydantic import ValidationError

    from aperix_geo.schemas.url_fields import normalize_validated_http_url

    s = raw.strip()
    if not s:
        return ""
    if not re.match(r"^https?://", s, re.I):
        s = f"http://{s.lstrip('/')}"
    try:
        validated = normalize_validated_http_url(s)
    except ValidationError:
        return ""
    host = host_from_url(validated)
    if not host or not is_brand_domain(host):
        return ""
    return validated


def explicit_http_url(raw: str) -> str:
    """仅接受输入已含 http:// 或 https:// 的 URL（拒绝裸域名，避免变体探测）。"""
    text = raw.strip()
    if not text or not re.match(r"^https?://", text, re.I):
        return ""
    return parse_url(text)


def coalesce_explicit_http_url(*raw_candidates: str) -> str:
    """按序取第一个合法完整 http(s) URL。"""
    for raw in raw_candidates:
        url = explicit_http_url(raw)
        if url:
            return url
    return ""


def homepage_fetch_urls(
    domain: str,
    *,
    website_url: str = "",
    probe_variants: bool = False,
) -> list[str]:
    """首页类抓取 URL 列表。

    - ``website_url`` 非空：只试完整 http(s) 或 bare host 单次 ``parse_url``，不 www/http 变体探测
    - ``website_url`` 为空且 ``probe_variants``：``website_candidates(domain)``（仅 SearXNG 等无 URL 兜底）
    """
    raw = website_url.strip()
    if raw:
        url = explicit_http_url(raw)
        if url:
            return [url]
        single = parse_url(raw)
        return [single] if single else []
    if probe_variants:
        return website_candidates(domain, preferred_url="")
    return []


def profile_homepage_fetch_urls(
    *,
    user_url: str,
    domain: str,
    root: str,
) -> list[str]:
    """Discover 主体首页：有 user_url 时单链；否则 ``profile_crawl_urls`` 兜底。"""
    if user_url.strip():
        host = registrable_from(domain or user_url) or root
        return homepage_fetch_urls(host, website_url=user_url, probe_variants=False)
    return profile_crawl_urls(user_url or domain, root=root)


def profile_crawl_urls(raw_input: str, *, root: str) -> list[str]:
    """Setup 画像首页抓取顺序：用户输入的完整 URL 优先，失败后再试 apex/www 候选。"""
    urls: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = u.strip()
        if not u or u in seen:
            return
        seen.add(u)
        urls.append(u)

    user = parse_url(raw_input)
    if user:
        add(user)
        parsed = urlparse(user)
        if parsed.scheme and parsed.netloc and parsed.path in ("", "/"):
            add(f"{parsed.scheme}://{parsed.netloc}/")

    if root:
        for u in apex_homepage_urls(root):
            add(u)
    return urls


def website_root_url(url: str) -> str:
    """保留 scheme + host，去掉 path/query/fragment 与末尾斜杠。"""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    host = parsed.netloc.lower().split(":")[0]
    return f"{parsed.scheme.lower()}://{host}"


def website_fallback(domain: str) -> str:
    """无网络探测时的默认首页 URL（优先 www + HTTPS）。"""
    root = registrable_domain(domain)
    if not root:
        return ""
    if host_resolves(f"www.{root}"):
        return f"https://www.{root}"
    return f"https://{root}"


def _probe_reachable_root_url(url: str, *, timeout_s: float, client: httpx.Client) -> str | None:
    try:
        resp = client.get(url, follow_redirects=True, timeout=timeout_s)
        if resp.status_code < 400:
            return website_root_url(str(resp.url))
    except httpx.HTTPError:
        return None
    return None


def resolve_website(raw: str, *, timeout_s: float = 5.0, probe: bool = True) -> tuple[str, str]:
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
                for candidate in website_candidates(domain):
                    resolved = _probe_reachable_root_url(candidate, timeout_s=timeout_s, client=client)
                    if resolved:
                        return domain, resolved
        except OSError:
            pass

    return domain, website_fallback(domain)
