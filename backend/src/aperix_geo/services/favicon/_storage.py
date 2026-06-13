"""In-memory and on-disk favicon cache."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlparse

from aperix_geo.config import get_settings

_CACHE_TTL_S = 86_400
_CACHE_MAX = 500
_NEGATIVE_CACHE_TTL_S = 6 * 3600
_NEGATIVE_CACHE_MAX = 2_000
_MEDIA_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
}

_cache: dict[str, tuple[float, bytes, str]] = {}
_negative_cache: dict[str, float] = {}


def negative_cache_hit(domain: str) -> bool:
    expires = _negative_cache.get(domain)
    if expires is None:
        return False
    if time.monotonic() > expires:
        _negative_cache.pop(domain, None)
        return False
    return True


def negative_cache_set(domain: str) -> None:
    if len(_negative_cache) >= _NEGATIVE_CACHE_MAX:
        oldest = min(_negative_cache.items(), key=lambda x: x[1])[0]
        _negative_cache.pop(oldest, None)
    _negative_cache[domain] = time.monotonic() + _NEGATIVE_CACHE_TTL_S


def _storage_root() -> Path:
    root = Path(get_settings().favicon_storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_storage_dir() -> Path:
    """启动时创建 favicon 持久化根目录（懒写入，首次抓取后才有域名子目录）。"""
    return _storage_root()


def _domain_store_dir(domain: str) -> Path:
    return _storage_root() / domain


def _index_path(domain: str) -> Path:
    return _domain_store_dir(domain) / "index.json"


def _ext_for(media_type: str, url: str) -> str:
    mt = media_type.split(";")[0].strip().lower()
    if mt in _MEDIA_EXT:
        return _MEDIA_EXT[mt]
    path = urlparse(url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".bin"


def _static_filename(media_type: str, url: str) -> str:
    return f"favicon{_ext_for(media_type, url)}"


def load_index(domain: str) -> dict:
    path = _index_path(domain)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_index(domain: str, index: dict) -> None:
    store = _domain_store_dir(domain)
    store.mkdir(parents=True, exist_ok=True)
    _index_path(domain).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def static_favicon_path(domain: str) -> tuple[Path, str] | None:
    """Fixed ``favicon.{ext}`` path for static URL serving."""
    store = _domain_store_dir(domain)
    index = load_index(domain)
    static = index.get("static")
    if not static:
        return None
    path = store / str(static)
    if not path.is_file():
        return None
    media_type = str(index.get("media_type") or "image/x-icon")
    return path, media_type


def read_disk_favicon(domain: str) -> tuple[bytes, str] | None:
    hit = static_favicon_path(domain)
    if hit is None:
        return None
    path, media_type = hit
    return path.read_bytes(), media_type


def read_cached_favicon(host: str) -> tuple[bytes, str] | None:
    """Memory cache, then on-disk favicon (promotes disk hit into memory)."""
    if row := cache_get(host):
        return row
    if stored := read_disk_favicon(host):
        body, media = stored
        cache_set(host, body, media)
        return stored
    return None


def cache_get(domain: str) -> tuple[bytes, str] | None:
    row = _cache.get(domain)
    if not row:
        return None
    expires, body, media = row
    if time.monotonic() > expires:
        _cache.pop(domain, None)
        return None
    return body, media


def cache_set(domain: str, body: bytes, media_type: str) -> None:
    if len(_cache) >= _CACHE_MAX:
        oldest = min(_cache.items(), key=lambda x: x[1][0])[0]
        _cache.pop(oldest, None)
    _cache[domain] = (time.monotonic() + _CACHE_TTL_S, body, media_type)


def persist_favicon(
    domain: str,
    *,
    url: str,
    body: bytes,
    media_type: str,
) -> None:
    store = _domain_store_dir(domain)
    store.mkdir(parents=True, exist_ok=True)
    static_name = _static_filename(media_type, url)
    for old in store.glob("favicon.*"):
        if old.name != static_name:
            old.unlink(missing_ok=True)
    (store / static_name).write_bytes(body)
    _write_index(
        domain,
        {
            "static": static_name,
            "media_type": media_type,
            "url": url,
        },
    )
    _negative_cache.pop(domain, None)
    cache_set(domain, body, media_type)
