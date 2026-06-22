"""站点 favicon 解析与缓存。

入口：``GET /api/v1/favicon?url=...`` → ``resolve_favicon``。

读取：内存（24h）→ 磁盘 favicon.{ext}（FileResponse 直出）→ 网络抓取（静态路径 → HTML link/meta → Crawl4AI 渲染兜底）。
未命中结果 negative cache 6h；并发同域请求 single-flight 合并。采样引用页抓取成功时会顺带从 HTML 解析并缓存 favicon。

磁盘：``{FAVICON_STORAGE_DIR}/{domain}/favicon.{ext}`` + ``index.json``（按 domain 键，不按 URL path）；磁盘命中时 API 走 FileResponse。

网络抓取走统一 ``services/crawl``（``get_icon_httpx_client`` / ``fetch_page`` / ``fetch_url_crawl4ai``）。
"""

from __future__ import annotations

import asyncio

from aperix_geo.services.favicon._domain import normalize_favicon_domain
from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced
from aperix_geo.services.favicon._storage import (
    ensure_storage_dir,
    negative_cache_hit,
    read_cached_favicon,
)
from aperix_geo.utils.domains import is_valid_hostname

_DEFAULT_TIMEOUT_S = 5.0

__all__ = [
    "ensure_storage_dir",
    "normalize_favicon_domain",
    "resolve_favicon",
]


async def resolve_favicon(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    """Network resolve; ``domain`` is the memory/disk cache key, ``page_url`` drives fetch."""
    host = normalize_favicon_domain(domain)
    if not host or not is_valid_hostname(host):
        return None

    if not page_url and negative_cache_hit(host):
        return None

    if cached := read_cached_favicon(host):
        return cached

    return await asyncio.to_thread(
        resolve_favicon_coalesced,
        host,
        timeout_s=timeout_s,
        page_url=page_url,
    )
