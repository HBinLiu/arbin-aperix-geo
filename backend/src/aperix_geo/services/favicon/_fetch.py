"""Download favicon bytes and orchestrate network resolution."""

from __future__ import annotations

import base64
from urllib.parse import unquote_to_bytes, urlparse

import httpx

from aperix_geo.services.crawl._httpx import get_icon_httpx_client
from aperix_geo.services.favicon._candidates import discover_icon_url_batches
from aperix_geo.services.favicon._domain import favicon_homepage_urls
from aperix_geo.services.favicon._parse import dedupe_urls
from aperix_geo.services.favicon._storage import persist_favicon
from aperix_geo.utils.http import HTML_PAGE_FETCH_HEADERS
from aperix_geo.utils.net import explicit_http_url

_MAX_ICON_BYTES = 512_000
_MAX_ICON_SIDE_PX = 512
_CONNECT_TIMEOUT_S = 1.5


def _request_timeout(timeout_s: float) -> httpx.Timeout:
    return httpx.Timeout(timeout=timeout_s, connect=min(_CONNECT_TIMEOUT_S, timeout_s))


def _is_ssl_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(token in msg for token in ("certificate", "ssl", "tlsv1", "hostname mismatch"))


def _client_get(
    client: httpx.Client,
    url: str,
    *,
    timeout: httpx.Timeout,
    headers: dict[str, str] | None = None,
) -> httpx.Response | None:
    try:
        return client.get(url, follow_redirects=True, timeout=timeout, headers=headers)
    except httpx.HTTPError as exc:
        if not _is_ssl_error(exc):
            return None
    with httpx.Client(headers=client.headers, follow_redirects=True, verify=False) as insecure:
        try:
            return insecure.get(url, follow_redirects=True, timeout=timeout, headers=headers)
        except httpx.HTTPError:
            return None


def _referer_for_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return None


def sniff_image(body: bytes) -> bool:
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
    if len(body) >= 4 and body[:4] in (b"\x00\x00\x01\x00", b"\x00\x00\x02\x00"):
        return True
    return False


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
    size = _parse_png_size(body) or _parse_gif_size(body)
    if not size:
        return True
    w, h = size
    return w <= _MAX_ICON_SIDE_PX and h <= _MAX_ICON_SIDE_PX


def _decode_data_url(url: str) -> tuple[bytes, str] | None:
    if not url.startswith("data:") or "," not in url:
        return None
    header, payload = url.split(",", 1)
    if ";base64" in header:
        try:
            body = base64.b64decode(payload, validate=True)
        except ValueError:
            return None
    else:
        body = unquote_to_bytes(payload)
    media = header[5:].split(";")[0].strip() or "image/x-icon"
    if not media.startswith("image/") or not sniff_image(body):
        return None
    if len(body) > _MAX_ICON_BYTES:
        return None
    return body, media


def fetch_icon_bytes(
    client: httpx.Client,
    url: str,
    *,
    timeout_s: float,
) -> tuple[bytes, str] | None:
    if url.startswith("data:"):
        return _decode_data_url(url)

    req_headers: dict[str, str] = {}
    if referer := _referer_for_url(url):
        req_headers["Referer"] = referer
    resp = _client_get(
        client,
        url,
        timeout=_request_timeout(timeout_s),
        headers=req_headers or None,
    )
    if resp is None or resp.status_code >= 400:
        return None

    body = resp.content
    if not body or len(body) > _MAX_ICON_BYTES:
        return None

    ct = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ct.startswith("text/html") or not sniff_image(body):
        return None
    if not _is_reasonable_icon_raster(body):
        return None

    return body, _guess_media_type(url, resp.headers.get("content-type"), body)


def _warm_homepage_cookies(
    client: httpx.Client,
    domain: str,
    *,
    timeout_s: float,
    page_url: str | None = None,
) -> None:
    explicit = explicit_http_url(page_url.strip()) if page_url and page_url.strip() else ""
    homes = [explicit] if explicit else favicon_homepage_urls(domain)
    for home in homes:
        if _client_get(
            client,
            home,
            timeout=_request_timeout(timeout_s),
            headers=HTML_PAGE_FETCH_HEADERS,
        ):
            return


def fetch_first_icon(
    client: httpx.Client,
    host: str,
    candidates: list[str],
    *,
    timeout_s: float,
) -> tuple[bytes, str] | None:
    for url in dedupe_urls(candidates):
        got = fetch_icon_bytes(client, url, timeout_s=timeout_s)
        if not got:
            continue
        body, media = got
        persist_favicon(host, url=url, body=body, media_type=media)
        return body, media
    return None


def resolve_favicon_network(
    host: str,
    *,
    timeout_s: float,
    page_url: str | None = None,
) -> tuple[bytes, str] | None:
    client = get_icon_httpx_client()
    _warm_homepage_cookies(client, host, timeout_s=timeout_s, page_url=page_url)

    for batch in discover_icon_url_batches(host, timeout_s=timeout_s, page_url=page_url):
        if not batch:
            continue
        if result := fetch_first_icon(client, host, batch, timeout_s=timeout_s):
            return result
    return None
