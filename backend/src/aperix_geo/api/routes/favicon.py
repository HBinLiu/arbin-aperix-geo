"""Favicon proxy — 供前端 <img> 使用，无需 Bearer（浏览器不会带 Authorization）。"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from aperix_geo.services.favicon import resolve_favicon_request
from aperix_geo.services.favicon._domain import FaviconMode, normalize_favicon_request
from aperix_geo.services.favicon._storage import (
    cache_get,
    ensure_apex_alias,
    negative_cache_hit,
    static_favicon_path,
)

router = APIRouter(tags=["favicon"])

_CACHE_HIT_HEADERS = {"Cache-Control": "public, max-age=86400, immutable"}
_MISS_HEADERS = {"Cache-Control": "public, max-age=3600"}


def _ok(body: bytes, media_type: str) -> Response:
    return Response(content=body, media_type=media_type, headers=_CACHE_HIT_HEADERS)


@router.get("/favicon")
async def get_favicon(
    url: str = Query(..., min_length=1, max_length=2048),
) -> Response:
    req = normalize_favicon_request(url)
    if req is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid url")

    if req.mode is FaviconMode.HOME and negative_cache_hit(req.cache_key):
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    # Fast path: avoid thread pool when already on disk/memory.
    if cached := cache_get(req.cache_key):
        body, media_type = cached
        return _ok(body, media_type)

    if disk := static_favicon_path(req.cache_key):
        path, media_type = disk
        return FileResponse(path, media_type=media_type, headers=_CACHE_HIT_HEADERS)

    if req.mode is FaviconMode.HOME and req.cache_key == req.apex:
        if promoted := ensure_apex_alias(req.apex):
            body, media_type = promoted
            return _ok(body, media_type)

    # Subdomain PAGE: domain list often cached apex only — reuse without network.
    if req.cache_key != req.apex:
        if cached := cache_get(req.apex):
            body, media_type = cached
            return _ok(body, media_type)
        if disk := static_favicon_path(req.apex):
            path, media_type = disk
            return FileResponse(path, media_type=media_type, headers=_CACHE_HIT_HEADERS)
        if promoted := ensure_apex_alias(req.apex):
            body, media_type = promoted
            return _ok(body, media_type)

    result = await resolve_favicon_request(req)
    if not result:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_MISS_HEADERS)

    body, media_type = result
    return _ok(body, media_type)
