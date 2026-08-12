"""站点 favicon 解析与缓存。

入口：``GET /api/v1/favicon?url=...`` → ``normalize_favicon_request`` → ``resolve_favicon``.

流水线：归一化 → 内存/磁盘 →（HOME+apex）子域 promote → 网络抓取 → 落盘（子域自动镜像 apex）。

磁盘：``{FAVICON_STORAGE_DIR}/{domain}/favicon.{ext}`` + ``index.json``；
HOME 抓取失败时 ``index.json`` 记 ``miss: true``，重启后仍跳过网络（成功 persist 会清除）。
"""

from __future__ import annotations

import asyncio

from aperix_geo.services.favicon._domain import FaviconRequest, favicon_from, normalize_favicon_request
from aperix_geo.services.favicon._resolve import resolve_favicon_sync
from aperix_geo.services.favicon._storage import ensure_storage_dir
from aperix_geo.utils.net import is_valid_hostname

_DEFAULT_TIMEOUT_S = 5.0

__all__ = [
    "ensure_storage_dir",
    "favicon_from",
    "normalize_favicon_request",
    "resolve_favicon",
    "resolve_favicon_request",
]


async def resolve_favicon_request(
    req: FaviconRequest,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> tuple[bytes, str] | None:
    """Resolve a normalized FaviconRequest (single pipeline entry)."""
    return await asyncio.to_thread(resolve_favicon_sync, req, timeout_s=timeout_s)


async def resolve_favicon(
    domain: str,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    """Legacy entry: ``domain`` + optional ``page_url`` → FaviconRequest → resolve."""
    from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced

    host = favicon_from(domain)
    if not host or not is_valid_hostname(host):
        return None
    return await asyncio.to_thread(
        resolve_favicon_coalesced,
        host,
        timeout_s=timeout_s,
        page_url=page_url,
    )
