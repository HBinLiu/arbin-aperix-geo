"""Favicon proxy — 供前端 <img> 使用，无需 Bearer（浏览器不会带 Authorization）。"""

from fastapi import APIRouter, HTTPException, Query, Response, status

from aperix_geo.utils.domains import is_valid_hostname
from aperix_geo.services.favicon import normalize_favicon_domain, resolve_favicon

router = APIRouter(tags=["favicon"])


@router.get("/favicon")
async def get_favicon(domain: str = Query(..., min_length=1, max_length=255)) -> Response:
    host = normalize_favicon_domain(domain)
    if not host or not is_valid_hostname(host):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid domain")

    result = await resolve_favicon(host)
    if not result:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    body, media_type = result
    return Response(
        content=body,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
