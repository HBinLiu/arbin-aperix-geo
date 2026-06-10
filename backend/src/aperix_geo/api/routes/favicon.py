"""Favicon proxy — 供前端 <img> 使用，无需 Bearer（浏览器不会带 Authorization）。"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from aperix_geo.services.favicon import normalize_favicon_domain, resolve_favicon
from aperix_geo.services.favicon._storage import (
    cache_get,
    negative_cache_hit,
    static_favicon_path,
)
from aperix_geo.utils.domains import is_valid_hostname

router = APIRouter(tags=["favicon"])

_CACHE_HIT_HEADERS = {"Cache-Control": "public, max-age=86400, immutable"}
_MISS_HEADERS = {"Cache-Control": "public, max-age=3600"}


def _normalize_host(domain: str) -> str:
    host = normalize_favicon_domain(domain)
    if not host or not is_valid_hostname(host):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid domain")
    return host


@router.get("/favicon")
async def get_favicon(
    domain: str = Query(..., min_length=1, max_length=255),
    page_url: str | None = Query(None, max_length=2048),
) -> Response:
    host = _normalize_host(domain)
    page_url = (page_url or "").strip() or None

    if not page_url and negative_cache_hit(host):
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    if cached := cache_get(host):
        body, media_type = cached
        return Response(content=body, media_type=media_type, headers=_CACHE_HIT_HEADERS)

    if disk := static_favicon_path(host):
        path, media_type = disk
        return FileResponse(path, media_type=media_type, headers=_CACHE_HIT_HEADERS)

    result = await resolve_favicon(host, page_url=page_url)
    if not result:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    body, media_type = result
    return Response(content=body, media_type=media_type, headers=_CACHE_HIT_HEADERS)
