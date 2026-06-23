"""Parse icon URLs from HTML (link, meta, related asset hosts)."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin, urlparse

from aperix_geo.utils.net import host_from

_LINK_TAG_RE = re.compile(r"<link\b([^>]+)>", re.IGNORECASE)
_META_TAG_RE = re.compile(r"<meta\b([^>]+)>", re.IGNORECASE)
_ATTR_RE = re.compile(
    r"""\b([a-zA-Z_:.-]+)\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)
_HTML_ASSET_HOST_RE = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_META_IMAGE_PROPS = frozenset({"og:image", "twitter:image", "twitter:image:src"})
_LINK_ATTR_NAMES = frozenset({"rel", "href", "type", "sizes"})
_QUICK_FAVICON_PATHS = ("/favicon.ico", "/favicon.png", "/apple-touch-icon.png")


def dedupe_urls(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def _resolve_href(page_url: str, href: str) -> str | None:
    href = unescape(href.strip())
    if not href or href.startswith(("javascript:", "mailto:", "tel:")):
        return None
    if href.startswith("data:"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    scheme = urlparse(href).scheme.lower()
    if scheme in ("http", "https"):
        return href
    return urljoin(page_url, href)


def _parse_sizes_rank(sizes: str) -> int:
    sizes = sizes.lower().strip()
    if not sizes:
        return 32
    best = 0
    for part in sizes.split():
        part = part.strip()
        if "x" not in part:
            continue
        try:
            w, _h = part.split("x", 1)
            best = max(best, int(w.strip()))
        except ValueError:
            continue
    return best or 32


def _parse_tag_attrs(attr_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, val in _ATTR_RE.findall(attr_text):
        attrs[key.lower()] = val.strip()
    for name in _LINK_ATTR_NAMES:
        if name in attrs:
            continue
        m = re.search(rf"""\b{name}\s*=\s*([^\s>'"]+)""", attr_text, re.IGNORECASE)
        if m:
            attrs[name] = m.group(1).strip()
    return attrs


def _split_rel_tokens(rel: str) -> list[str]:
    return [t for t in re.split(r"[\s,]+", rel.lower().strip()) if t]


def _classify_link_rel(rel: str) -> int | None:
    rel_l = rel.lower().strip()
    rel_tokens = _split_rel_tokens(rel_l)
    if "apple-touch-icon" in rel_l:
        return 0
    if "icon" not in rel_tokens:
        return None
    if "fluid-icon" in rel_l or "mask-icon" in rel_l:
        return 2
    if "shortcut" in rel_tokens:
        return 1
    return 1


def parse_link_icons(html: str, page_url: str) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for m in _LINK_TAG_RE.finditer(html):
        attrs = _parse_tag_attrs(m.group(1))
        rel = attrs.get("rel", "")
        rank = _classify_link_rel(rel)
        if rank is None:
            continue
        href = attrs.get("href", "").strip()
        if not href:
            continue
        resolved = _resolve_href(page_url, href)
        if not resolved:
            continue
        size_rank = -_parse_sizes_rank(attrs.get("sizes", ""))
        ranked.append((rank, size_rank, resolved))
    ranked.sort(key=lambda x: (x[0], x[1], x[2]))
    return list(dict.fromkeys(u for _, _, u in ranked))


def parse_meta_images(html: str, page_url: str) -> list[str]:
    found: list[str] = []
    for m in _META_TAG_RE.finditer(html):
        attrs = _parse_tag_attrs(m.group(1))
        prop = (attrs.get("property") or attrs.get("name") or "").lower()
        if prop not in _META_IMAGE_PROPS:
            continue
        content = attrs.get("content", "").strip()
        resolved = _resolve_href(page_url, content) if content else None
        if resolved:
            found.append(resolved)
    return list(dict.fromkeys(found))


def _host_belongs_to_domain(host: str, root_domain: str) -> bool:
    h = host.lower().strip(".")
    root = root_domain.lower()
    return h == root or h.endswith(f".{root}")


def related_hosts_from_html(html: str, root_domain: str) -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()
    for m in _HTML_ASSET_HOST_RE.finditer(html):
        raw = unescape(m.group(1).strip())
        if not raw or raw.startswith(("javascript:", "data:", "mailto:", "#")):
            continue
        if raw.startswith("//"):
            raw = f"https:{raw}"
        host = host_from(raw if "://" in raw else f"https://{raw.lstrip('/')}")
        if not host or not _host_belongs_to_domain(host, root_domain):
            continue
        if host in seen:
            continue
        seen.add(host)
        hosts.append(host)
    return hosts


def favicon_urls_for_hosts(hosts: list[str]) -> list[str]:
    urls: list[str] = []
    for host in hosts:
        base = f"https://{host}/"
        for path in _QUICK_FAVICON_PATHS:
            urls.append(urljoin(base, path))
    return dedupe_urls(urls)


def page_icon_candidates_from_html(html: str, page_url: str) -> list[str]:
    """``link rel=icon`` and og/twitter image meta from page HTML."""
    return dedupe_urls(parse_link_icons(html, page_url) + parse_meta_images(html, page_url))


def _related_subdomain_hosts(html: str, root_domain: str) -> list[str]:
    """Asset hosts under the registrable domain, excluding apex and www."""
    root = root_domain.lower().strip()
    www = f"www.{root}"
    hosts = related_hosts_from_html(html, root_domain)
    return [h for h in hosts if h.lower() not in (root, www)]


def subdomain_favicon_candidates_from_html(html: str, root_domain: str) -> list[str]:
    """Probe ``/favicon.ico`` on non-www subdomains referenced in HTML (low priority)."""
    return favicon_urls_for_hosts(_related_subdomain_hosts(html, root_domain))


def icon_candidates_from_html(html: str, page_url: str, domain: str) -> list[str]:
    return dedupe_urls(
        page_icon_candidates_from_html(html, page_url)
        + subdomain_favicon_candidates_from_html(html, domain),
    )
