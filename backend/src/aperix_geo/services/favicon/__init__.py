"""站点 favicon 解析与缓存。

入口：``GET /api/v1/favicon?domain=...`` → ``resolve_favicon``。

读取：内存（24h）→ 磁盘 primary（FileResponse 直出）→ 网络抓取（静态路径 → HTML link/meta → Crawl4AI 渲染兜底）。
未命中结果 negative cache 6h；并发同域请求 single-flight 合并。采样 job 完成后 Celery 后台预热 citation 域名 favicon。

磁盘：``{FAVICON_STORAGE_DIR}/{domain}/favicon.{ext}`` + ``index.json``；磁盘命中时 API 走 FileResponse。

网络抓取走统一 ``services/crawl``（``get_icon_httpx_client`` / ``fetch_page`` / ``fetch_url_crawl4ai``）。
"""

from __future__ import annotations

import asyncio

from aperix_geo.services.favicon._candidates import icons_from_crawl4ai, icons_from_fetch_page
from aperix_geo.services.favicon._domain import normalize_favicon_domain
from aperix_geo.services.favicon._fetch import resolve_favicon_network, sniff_image
from aperix_geo.services.favicon._parse import (
    favicon_urls_for_hosts,
    icon_candidates_from_html,
    page_icon_candidates_from_html,
    parse_link_icons,
    parse_meta_images,
    related_hosts_from_html,
    subdomain_favicon_candidates_from_html,
)
from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced
from aperix_geo.services.favicon._storage import (
    cache_get,
    cache_set,
    ensure_storage_dir,
    load_index,
    load_primary_from_disk,
    negative_cache_hit,
    persist_icon,
    primary_file_path,
)
from aperix_geo.utils.domains import is_valid_hostname

_DEFAULT_TIMEOUT_S = 5.0

__all__ = [
    "ensure_storage_dir",
    "normalize_favicon_domain",
    "resolve_favicon",
]

# 测试兼容：旧模块级私有名
_parse_link_icons = parse_link_icons
_parse_meta_images = parse_meta_images
_sniff_image = sniff_image
_icon_candidates_from_html = icon_candidates_from_html
_page_icon_candidates_from_html = page_icon_candidates_from_html
_subdomain_favicon_candidates_from_html = subdomain_favicon_candidates_from_html
_related_hosts_from_html = related_hosts_from_html
_favicon_urls_for_hosts = favicon_urls_for_hosts
_persist_icon = persist_icon
_load_index = load_index
_load_primary_from_disk = load_primary_from_disk
_icons_from_fetch_page = icons_from_fetch_page
_icons_from_crawl4ai = icons_from_crawl4ai
_resolve_favicon_network = resolve_favicon_network


async def resolve_favicon(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    host = normalize_favicon_domain(domain)
    if not host or not is_valid_hostname(host):
        return None

    if not page_url and negative_cache_hit(host):
        return None

    if cached := cache_get(host):
        return cached

    if stored := primary_file_path(host):
        path, media_type = stored
        body = path.read_bytes()
        cache_set(host, body, media_type)
        return body, media_type

    return await asyncio.to_thread(
        resolve_favicon_coalesced,
        host,
        timeout_s=timeout_s,
        page_url=page_url,
    )
