"""Favicon proxy — 供前端 <img> 使用，无需 Bearer（浏览器不会带 Authorization）。"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from aperix_geo.services.favicon import resolve_favicon
from aperix_geo.services.favicon._domain import is_favicon_homepage_url, resolve_favicon_request_url
from aperix_geo.services.favicon._storage import (
    cache_get,
    negative_cache_hit,
    static_favicon_path,
)

router = APIRouter(tags=["favicon"])

_CACHE_HIT_HEADERS = {"Cache-Control": "public, max-age=86400, immutable"}
_MISS_HEADERS = {"Cache-Control": "public, max-age=3600"}


@router.get("/favicon")
async def get_favicon(
    url: str = Query(..., min_length=1, max_length=2048),
) -> Response:
    resolved = resolve_favicon_request_url(url)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid url")

    domain, page_url = resolved

    if is_favicon_homepage_url(page_url, domain) and negative_cache_hit(domain):
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    if cached := cache_get(domain):
        body, media_type = cached
        return Response(content=body, media_type=media_type, headers=_CACHE_HIT_HEADERS)

    if disk := static_favicon_path(domain):
        path, media_type = disk
        return FileResponse(path, media_type=media_type, headers=_CACHE_HIT_HEADERS)

    result = await resolve_favicon(domain, page_url=page_url)
    if not result:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    body, media_type = result
    return Response(content=body, media_type=media_type, headers=_CACHE_HIT_HEADERS)
