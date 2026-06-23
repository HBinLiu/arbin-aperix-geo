"""主域名归一、格式校验、站点名提取。"""

from __future__ import annotations

import re
from functools import lru_cache

from publicsuffix2 import PublicSuffixList
from validators import domain as validators_domain

_TITLE_SEP_RE = re.compile(r"[|｜\-—_/·]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_TITLE_NOISE = (
    "官网",
    "官方网站",
    "首页",
    "官方首页",
    "Home",
    "HOME",
    "Official Site",
    "Welcome to",
)


@lru_cache(maxsize=1)
def _public_suffix_list() -> PublicSuffixList:
    return PublicSuffixList()


def strip_hostname(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0].split("?")[0].strip()
    if s.startswith("www."):
        s = s[4:]
    return s


def normalize_host(raw: str | None) -> str:
    """Lowercase hostname without scheme/www; preserves subdomains."""
    if not raw:
        return ""
    return strip_hostname(raw)


def host_from(value: str | None) -> str:
    """Extract normalized host from a URL, bare hostname, or domain field."""
    text = (value or "").strip()
    if not text:
        return ""
    if "://" in text or text.startswith("//"):
        from aperix_geo.utils.url import host_from_url

        url = text if not text.startswith("//") else f"https:{text}"
        return host_from_url(url) or ""
    return normalize_host(text)


def registrable_from(value: str | None) -> str:
    """eTLD+1 from a URL or hostname string."""
    host = host_from(value)
    return registrable_domain(host) if host else ""


def brand_from(raw: str | None) -> str:
    """Validated brand primary domain (eTLD+1)."""
    text = (raw or "").strip()
    if not text or not is_brand_domain(text):
        return ""
    return registrable_domain(text)


def favicon_from(raw: str | None) -> str:
    """Favicon cache key: eTLD+1 for apex hosts; keep full host for meaningful subdomains."""
    host = host_from(raw).split(":")[0]
    if not host:
        return ""
    root = registrable_domain(host)
    if root and host != root and host.endswith(f".{root}"):
        return host
    return root or host


def registrable_domain(raw: str) -> str:
    """eTLD+1 via Public Suffix List (strict)."""
    host = strip_hostname(raw)
    if not host:
        return ""
    sld = _public_suffix_list().get_sld(host, strict=True)
    return (sld or "").strip().lower()


def dedupe_domains(hosts: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for h in hosts:
        rd = registrable_domain(h)
        if not rd or rd in seen:
            continue
        seen.add(rd)
        out.append(rd)
    return out


def is_valid_hostname(host: str) -> bool:
    text = strip_hostname(host) if "://" in (host or "") else (host or "").strip().lower()
    if not text or len(text) > 253:
        return False
    return bool(validators_domain(text))


def is_brand_domain(raw: str) -> bool:
    """RFC domain format (validators) + registrable domain in PSL (publicsuffix2 strict)."""
    host = strip_hostname(raw)
    if not host:
        return False
    if not validators_domain(host):
        return False
    return _public_suffix_list().get_sld(host, strict=True) is not None


def brand_fallback(raw: str) -> str:
    """brand 为空时，用主域名（eTLD+1）兜底。"""
    return registrable_domain(raw)


def ensure_brand(brand: str | None, *, domain: str | None = None) -> str:
    """返回非空 brand；缺失且提供了 domain 时回退为主域名。"""
    name = (brand or "").strip()
    if name:
        return name[:255]
    dom = (domain or "").strip()
    if dom:
        return brand_fallback(dom)[:255]
    return ""


def site_name_from_title(title: str, *, domain: str) -> str:
    text = title.strip()
    if text:
        parts = _TITLE_SEP_RE.split(text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if _CJK_RE.search(part):
                cleaned = part
                for noise in _TITLE_NOISE:
                    cleaned = cleaned.replace(noise, "").strip()
                if cleaned:
                    return cleaned[:60]
        text = parts[0].strip() if parts else text
        for noise in _TITLE_NOISE:
            text = text.replace(noise, "").strip()
        if text and len(text) <= 60:
            return text

    fallback = brand_fallback(domain)
    return fallback or normalize_host(domain)
