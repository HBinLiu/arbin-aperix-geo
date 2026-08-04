"""主域名归一、格式校验、站点名提取。"""

from __future__ import annotations

import re
from functools import lru_cache

from publicsuffix2 import PublicSuffixList
from validators import domain as validators_domain

_TITLE_SEP_RE = re.compile(r"[\s|｜\-—_/·]+")
# 站点名推导用「强分隔符」，避免把 "Aperix AI" 拆成单词
_SITE_TITLE_SEP_RE = re.compile(r"\s*[|｜_/·]+\s*|\s+[—\-]\s+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
# 与 crawl.seo.MAX_SITE_NAME_LEN 对齐：标题分段里可接受的品牌侧长度
_SITE_NAME_PART_MAX = 20
_TITLE_ALIAS_SEP_RE = re.compile(r"[\s|｜\-—_/·+:：]+")
_LATIN_ALIAS_BLOCKLIST = frozenset(
    {
        "send",
        "money",
        "home",
        "online",
        "payment",
        "payments",
        "global",
        "official",
        "welcome",
        "website",
        "app",
        "platform",
        "service",
        "services",
        "solutions",
        "company",
        "group",
        "inc",
        "ltd",
        "corp",
    }
)
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


def _latin_title_token_as_alias(token: str) -> bool:
    text = token.strip()
    if len(text) < 3 or len(text) > 40:
        return False
    if text.casefold() in _LATIN_ALIAS_BLOCKLIST:
        return False
    if any(c.isupper() for c in text[1:]):
        return True
    if text[0].isupper() and not text.isupper():
        return len(text) >= 6
    return False


def _clean_title_part(raw: str) -> str:
    text = (raw or "").strip()
    for noise in _TITLE_NOISE:
        text = text.replace(noise, "").strip()
    return text.strip(":：;；,.，。").strip()


def title_alias_candidates(title: str, *, domain: str, brand: str) -> list[str]:
    """从页面 title 提取可作竞品别名的候选（不含 canonical brand）。"""
    brand_key = brand.casefold()
    seen: set[str] = {brand_key}
    out: list[str] = []

    def add(candidate: str) -> None:
        text = _clean_title_part(candidate)[:120]
        if len(text) < 2:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        out.append(text)

    site = site_name_from_title(title, domain=domain)
    if site and site.casefold() != brand_key:
        if _CJK_RE.search(site):
            add(site)
        elif _latin_title_token_as_alias(site):
            add(site)

    for part in _TITLE_ALIAS_SEP_RE.split((title or "").strip()):
        part = _clean_title_part(part)
        if not part:
            continue
        if part.casefold() == brand_key:
            continue
        if _CJK_RE.search(part):
            if len(part) <= 60:
                add(part)
            continue
        if _latin_title_token_as_alias(part):
            add(part)

    return out


def site_name_from_title(title: str, *, domain: str) -> str:
    """Derive a brand-like site name from a document title.

    Prefer the shorter brand side of ``文章标题 | 站点名`` / ``站点名 | 副标题``.
    """
    text = title.strip()
    if text:
        raw_parts = [p.strip() for p in _SITE_TITLE_SEP_RE.split(text) if p.strip()]

        def _clean_part(part: str) -> str:
            cleaned = part
            for noise in _TITLE_NOISE:
                cleaned = cleaned.replace(noise, "").strip()
            return cleaned.strip(":：;；,.，。").strip()

        parts = [_clean_part(p) for p in raw_parts]
        parts = [p for p in parts if p]

        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
            # 「长文章标题 | 品牌」→ 较短尾部；「品牌 | 副标题」→ 较短头部
            if len(last) <= _SITE_NAME_PART_MAX and len(last) < len(first):
                return last[:_SITE_NAME_PART_MAX]
            # 中文长标题 + 英文品牌（长度接近时）
            if (
                len(last) <= _SITE_NAME_PART_MAX
                and len(first) >= 8
                and _CJK_RE.search(first)
                and not _CJK_RE.search(last)
            ):
                return last[:_SITE_NAME_PART_MAX]
            if len(first) <= _SITE_NAME_PART_MAX:
                return first[:_SITE_NAME_PART_MAX]
            shorter = last if len(last) <= len(first) else first
            if len(shorter) <= _SITE_NAME_PART_MAX:
                return shorter[:_SITE_NAME_PART_MAX]

        if len(parts) == 1:
            part = parts[0]
            for sep in (":", "："):
                if sep in part:
                    left = _clean_part(part.split(sep, 1)[0])
                    if left and len(left) <= _SITE_NAME_PART_MAX:
                        part = left
                        break
            if _CJK_RE.search(part):
                return part[:_SITE_NAME_PART_MAX] if len(part) <= _SITE_NAME_PART_MAX else ""
            # 多词英文更像描述，不当作站点名
            if " " in part and len(part) > 16:
                pass
            elif part and len(part) <= _SITE_NAME_PART_MAX:
                return part

        for part in parts:
            if _CJK_RE.search(part) and len(part) <= _SITE_NAME_PART_MAX:
                return part
        if parts and len(parts[0]) <= _SITE_NAME_PART_MAX and " " not in parts[0]:
            return parts[0]

    fallback = brand_fallback(domain)
    return fallback or normalize_host(domain)
