"""站点 favicon：解析首页 link、常见路径、魔数校验与内存缓存。"""

from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from aperix_geo.utils.domains import (
    is_valid_hostname,
    registrable_domain,
    strip_hostname,
)
from aperix_geo.utils.http import HTML_PAGE_FETCH_HEADERS, ICON_FETCH_HEADERS
from aperix_geo.utils.url import homepage_urls

_HTML_FETCH_HEADERS = HTML_PAGE_FETCH_HEADERS

_MAX_ICON_BYTES = 512_000
_MAX_ICON_SIDE_PX = 512
_MAX_HOMEPAGE_HTML_CHARS = 200_000
_MAX_RENDERED_HTML_CHARS = 400_000
_CACHE_TTL_S = 86_400
_CACHE_MAX = 500
_DEFAULT_TIMEOUT_S = 5.0
_CONNECT_TIMEOUT_S = 1.5
_HEADLESS_MIN_TIMEOUT_S = 8.0

_LINK_TAG_RE = re.compile(r"<link\b([^>]+)>", re.IGNORECASE)
_ATTR_RE = re.compile(
    r"""\b([a-zA-Z_:.-]+)\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)
_STANDARD_ICON_PATHS = (
    "/favicon.ico",
    "/favicon.png",
    "/favicon.svg",
    "/assets/favicon.ico",
    "/static/favicon.ico",
)

_cache: dict[str, tuple[float, bytes, str]] = {}


def _dedupe_urls(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def normalize_favicon_domain(raw: str) -> str:
    """
    统一为 eTLD+1 主域名（与竞品入库、前端 registrableDomain 一致）。

    接受：主域名、www、子域名、带路径的 URL、含端口的主机名片段。
    """
    host = registrable_domain(raw)
    if not host:
        host = strip_hostname(raw)
    if not host:
        return ""
    # 去掉可能残留的端口
    return host.split(":")[0].strip().lower()


def _cache_get(domain: str) -> tuple[bytes, str] | None:
    row = _cache.get(domain)
    if not row:
        return None
    expires, body, media = row
    if time.monotonic() > expires:
        _cache.pop(domain, None)
        return None
    return body, media


def _cache_set(domain: str, body: bytes, media_type: str) -> None:
    if len(_cache) >= _CACHE_MAX:
        oldest = min(_cache.items(), key=lambda x: x[1][0])[0]
        _cache.pop(oldest, None)
    _cache[domain] = (time.monotonic() + _CACHE_TTL_S, body, media_type)


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
    """越大越优先；未知 sizes 给中等分。"""
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


_LINK_ATTR_NAMES = frozenset({"rel", "href", "type", "sizes"})


def _parse_link_tag_attrs(attr_text: str) -> dict[str, str]:
    """解析 link 标签属性；支持引号包裹与无引号的 rel / href。"""
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
    """返回排序权重，越小越优先。"""
    rel_l = rel.lower().strip()
    rel_tokens = _split_rel_tokens(rel_l)
    if "icon" not in rel_tokens:
        return None
    if "apple-touch-icon" in rel_l:
        return 0
    if "fluid-icon" in rel_l or "mask-icon" in rel_l:
        return 2
    if "shortcut" in rel_tokens:
        return 1
    return 1


def _parse_link_icons(html: str, page_url: str) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for m in _LINK_TAG_RE.finditer(html):
        attrs = _parse_link_tag_attrs(m.group(1))
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


def _parse_icon_hrefs(html: str, page_url: str) -> list[str]:
    """兼容旧测试名：仅解析 link 图标候选。"""
    return _parse_link_icons(html, page_url)


def _standard_path_urls(domain: str) -> list[str]:
    urls: list[str] = []
    for home in homepage_urls(domain) or []:
        for path in _STANDARD_ICON_PATHS:
            urls.append(urljoin(home, path))
    return _dedupe_urls(urls)


def _guess_media_type(url: str, content_type: str | None, body: bytes) -> str:
    if content_type and content_type.split(";")[0].strip().startswith("image/"):
        return content_type.split(";")[0].strip()
    path = urlparse(url).path.lower()
    if path.endswith(".svg") or b"<svg" in body[:256].lower():
        return "image/svg+xml"
    if path.endswith(".png") or body.startswith(b"\x89PNG"):
        return "image/png"
    if path.endswith(".webp") or (body.startswith(b"RIFF") and b"WEBP" in body[:16]):
        return "image/webp"
    if path.endswith(".gif") or body.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if path.endswith((".jpg", ".jpeg")) or body.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/x-icon"


def _sniff_image(body: bytes) -> bool:
    if body.startswith(b"\x89PNG"):
        return True
    if body.startswith(b"\xff\xd8\xff"):
        return True
    if body.startswith((b"GIF87a", b"GIF89a")):
        return True
    if body.startswith(b"RIFF") and len(body) >= 12 and body[8:12] == b"WEBP":
        return True
    head = body[:512].lstrip()
    if head.startswith((b"<svg", b"<?xml")) and b"svg" in head[:200].lower():
        return True
    # ICO: ICON dir or embedded PNG
    if len(body) >= 4 and body[:4] in (b"\x00\x00\x01\x00", b"\x00\x00\x02\x00"):
        return True
    return False


def _decode_data_url(url: str) -> tuple[bytes, str] | None:
    if not url.startswith("data:") or "," not in url:
        return None
    header, payload = url.split(",", 1)
    if ";base64" in header:
        import base64

        try:
            body = base64.b64decode(payload, validate=True)
        except ValueError:
            return None
    else:
        from urllib.parse import unquote_to_bytes

        body = unquote_to_bytes(payload)
    media = header[5:].split(";")[0].strip() or "image/x-icon"
    if not media.startswith("image/") or not _sniff_image(body):
        return None
    if len(body) > _MAX_ICON_BYTES:
        return None
    return body, media


def _request_timeout(timeout_s: float) -> httpx.Timeout:
    return httpx.Timeout(timeout=timeout_s, connect=min(_CONNECT_TIMEOUT_S, timeout_s))


def _extract_crawl_html(result: object) -> str:
    for attr in ("html", "cleaned_html", "raw_html"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _parse_png_size(body: bytes) -> tuple[int, int] | None:
    if len(body) < 24 or not body.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    w = int.from_bytes(body[16:20], "big")
    h = int.from_bytes(body[20:24], "big")
    if w <= 0 or h <= 0:
        return None
    return w, h


def _parse_gif_size(body: bytes) -> tuple[int, int] | None:
    if len(body) < 10 or not body.startswith((b"GIF87a", b"GIF89a")):
        return None
    w = int.from_bytes(body[6:8], "little")
    h = int.from_bytes(body[8:10], "little")
    if w <= 0 or h <= 0:
        return None
    return w, h


def _is_reasonable_icon_raster(body: bytes) -> bool:
    """
    过滤明显不是 favicon 的大图（如 1920x1080 背景图）。
    未能解析尺寸时不拦截，避免误伤格式兼容性。
    """
    size = _parse_png_size(body) or _parse_gif_size(body)
    if not size:
        return True
    w, h = size
    return w <= _MAX_ICON_SIDE_PX and h <= _MAX_ICON_SIDE_PX


def _iter_crawl_results(raw: object) -> list[object]:
    if isinstance(raw, list):
        return raw
    if raw is None:
        return []
    return [raw]


async def _fetch_icon_bytes(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout_s: float,
) -> tuple[bytes, str] | None:
    if url.startswith("data:"):
        return _decode_data_url(url)

    try:
        resp = await client.get(
            url,
            follow_redirects=True,
            timeout=_request_timeout(timeout_s),
        )
    except httpx.HTTPError:
        return None

    if resp.status_code >= 400:
        return None

    body = resp.content
    if not body or len(body) > _MAX_ICON_BYTES:
        return None

    ct = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ct.startswith("text/html") or not _sniff_image(body):
        return None
    if not _is_reasonable_icon_raster(body):
        return None

    return body, _guess_media_type(url, resp.headers.get("content-type"), body)


async def _try_fetch_candidates(
    client: httpx.AsyncClient,
    host: str,
    candidates: list[str],
    *,
    timeout_s: float,
    source: str,
) -> tuple[tuple[bytes, str] | None, int]:
    """
    顺序尝试候选 URL，首个成功即返回。
    返回：(命中结果或 None, 实际尝试次数)。
    """
    attempted = 0
    for url in _dedupe_urls(candidates):
        attempted += 1
        got = await _fetch_icon_bytes(client, url, timeout_s=timeout_s)
        if got:
            return got, attempted
    return None, attempted


async def _icons_from_homepage(
    client: httpx.AsyncClient,
    domain: str,
    *,
    timeout_s: float,
) -> list[str]:
    found: list[str] = []
    for home in homepage_urls(domain) or []:
        try:
            resp = await client.get(
                home,
                follow_redirects=True,
                timeout=_request_timeout(timeout_s),
                headers=_HTML_FETCH_HEADERS,
            )
        except httpx.HTTPError:
            continue
        if resp.status_code >= 500:
            continue
        page_url = str(resp.url)
        html = resp.text[:_MAX_HOMEPAGE_HTML_CHARS]
        page_icons = _parse_icon_hrefs(html, page_url)
        if page_icons:
            found.extend(page_icons)
            break
    return _dedupe_urls(found)


async def _icons_from_rendered_homepage(domain: str, *, timeout_s: float) -> list[str]:
    """
    JS 渲染兜底：当原始 HTML 未给出 icon 时，使用 headless 渲染后再解析。
    """
    homes = homepage_urls(domain) or []
    if not homes:
        return []
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    except Exception:
        return []

    page_timeout_ms = max(5000, int(timeout_s * 1000))
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        verbose=False,
        page_timeout=page_timeout_ms,
    )

    try:
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
            for home in homes:
                try:
                    raw = await crawler.arun(home, config=config)
                except Exception:
                    continue
                for item in _iter_crawl_results(raw):
                    if not getattr(item, "success", True):
                        continue
                    page_url = str(getattr(item, "url", home) or home)
                    html = _extract_crawl_html(item)[:_MAX_RENDERED_HTML_CHARS]
                    if not html:
                        continue
                    page_icons = _parse_icon_hrefs(html, page_url)
                    if page_icons:
                        return page_icons
    except Exception:
        return []

    return []


async def resolve_favicon(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> tuple[bytes, str] | None:
    host = normalize_favicon_domain(domain)
    if not host or not is_valid_hostname(host):
        return None

    cached = _cache_get(host)
    if cached:
        return cached

    # 解析与抓取分为三阶段：
    # 1) 常见静态路径；2) 原始 HTML（link）；3) headless 渲染兜底。
    tried = 0
    standard_urls = _standard_path_urls(host)
    page_icons: list[str] = []
    rendered_icons: list[str] = []
    async with httpx.AsyncClient(headers=ICON_FETCH_HEADERS) as client:
        got, attempted = await _try_fetch_candidates(
            client,
            host,
            standard_urls,
            timeout_s=timeout_s,
            source="standard",
        )
        tried += attempted
        if got:
            body, media = got
            _cache_set(host, body, media)
            return body, media

        page_icons = await _icons_from_homepage(client, host, timeout_s=timeout_s)
        got, attempted = await _try_fetch_candidates(
            client,
            host,
            page_icons,
            timeout_s=timeout_s,
            source="homepage",
        )
        tried += attempted
        if got:
            body, media = got
            _cache_set(host, body, media)
            return body, media

        rendered_icons = await _icons_from_rendered_homepage(
            host,
            timeout_s=max(timeout_s, _HEADLESS_MIN_TIMEOUT_S),
        )
        got, attempted = await _try_fetch_candidates(
            client,
            host,
            rendered_icons,
            timeout_s=timeout_s,
            source="rendered",
        )
        tried += attempted
        if got:
            body, media = got
            _cache_set(host, body, media)
            return body, media

    return None
