"""主域名归一、格式校验、站点名提取。"""

from __future__ import annotations

import re

_HOSTNAME_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$",
)

_MULTIPART_SUFFIXES: frozenset[str] = frozenset(
    {
        "com.cn",
        "net.cn",
        "org.cn",
        "gov.cn",
        "edu.cn",
        "ac.cn",
        "co.uk",
        "org.uk",
        "com.au",
        "co.jp",
        "com.hk",
        "com.tw",
        "co.kr",
        "com.sg",
    },
)

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


def strip_hostname(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0].split("?")[0].strip()
    if s.startswith("www."):
        s = s[4:]
    return s


def registrable_domain(raw: str) -> str:
    host = strip_hostname(raw)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) < 2:
        return host
    suffix2 = ".".join(parts[-2:])
    if suffix2 in _MULTIPART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return suffix2


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
    return bool(host) and len(host) <= 253 and bool(_HOSTNAME_RE.match(host))


def brand_fallback_from_domain(raw: str) -> str:
    """brand 为空时，用主域名（eTLD+1）兜底。"""
    return registrable_domain(raw)


def ensure_brand(brand: str | None, *, domain: str | None = None) -> str:
    """返回非空 brand；缺失且提供了 domain 时回退为主域名。"""
    name = (brand or "").strip()
    if name:
        return name[:255]
    dom = (domain or "").strip()
    if dom:
        return brand_fallback_from_domain(dom)[:255]
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

    return brand_fallback_from_domain(domain) or domain
