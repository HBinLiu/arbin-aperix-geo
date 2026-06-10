"""In-memory and on-disk favicon cache."""

from __future__ import annotations

import hashlib
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


def _file_key_for_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _static_filename(media_type: str, url: str) -> str:
    return f"favicon{_ext_for(media_type, url)}"


def _media_type_for_primary(index: dict, primary_file: str) -> str:
    items = index.get("items") or []
    item = next((row for row in items if isinstance(row, dict) and row.get("file") == primary_file), None)
    if isinstance(item, dict):
        return str(item.get("media_type") or "image/x-icon")
    return "image/x-icon"


def _write_static_favicon(
    store: Path,
    index: dict,
    *,
    static_name: str,
    body: bytes,
) -> None:
    for old in store.glob("favicon.*"):
        if old.name != static_name:
            old.unlink(missing_ok=True)
    for old in store.glob("primary.*"):
        old.unlink(missing_ok=True)
    (store / static_name).write_bytes(body)
    index["static"] = static_name


def _migrate_legacy_static_file(
    domain: str,
    store: Path,
    index: dict,
    legacy_path: Path,
) -> tuple[Path, str] | None:
    media_type = _media_type_for_primary(index, str(index.get("primary") or legacy_path.name))
    static_name = f"favicon{legacy_path.suffix}"
    try:
        body = legacy_path.read_bytes()
        _write_static_favicon(store, index, static_name=static_name, body=body)
        _write_index(domain, index)
    except OSError:
        return legacy_path, media_type
    return store / static_name, media_type


def static_favicon_path(domain: str) -> tuple[Path, str] | None:
    """Fixed ``favicon.{ext}`` path for static URL serving (backfills legacy stores)."""
    store = _domain_store_dir(domain)
    index = load_index(domain)

    static = index.get("static")
    if static:
        path = store / str(static)
        if path.is_file():
            if path.name.startswith("primary."):
                return _migrate_legacy_static_file(domain, store, index, path)
            primary = index.get("primary")
            media_type = _media_type_for_primary(index, str(primary or ""))
            return path, media_type

    for path in sorted(store.glob("favicon.*")):
        index["static"] = path.name
        _write_index(domain, index)
        primary = index.get("primary")
        media_type = _media_type_for_primary(index, str(primary or path.name))
        return path, media_type

    for path in sorted(store.glob("primary.*")):
        migrated = _migrate_legacy_static_file(domain, store, index, path)
        if migrated:
            return migrated

    hit = primary_file_path(domain)
    if hit is None:
        return None
    path, media_type = hit
    static_name = _static_filename(media_type, path.name)
    try:
        _write_static_favicon(store, index, static_name=static_name, body=path.read_bytes())
        _write_index(domain, index)
    except OSError:
        return path, media_type
    return store / static_name, media_type


def load_index(domain: str) -> dict:
    path = _index_path(domain)
    if not path.is_file():
        return {"primary": None, "static": None, "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"primary": None, "static": None, "items": []}
    if not isinstance(data, dict):
        return {"primary": None, "static": None, "items": []}
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    return {"primary": data.get("primary"), "static": data.get("static"), "items": items}


def _write_index(domain: str, index: dict) -> None:
    store = _domain_store_dir(domain)
    store.mkdir(parents=True, exist_ok=True)
    _index_path(domain).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def load_primary_from_disk(domain: str) -> tuple[bytes, str] | None:
    hit = primary_file_path(domain)
    if hit is None:
        return None
    path, media_type = hit
    return path.read_bytes(), media_type


def primary_file_path(domain: str) -> tuple[Path, str] | None:
    """Return primary icon path + media type without reading file bytes."""
    index = load_index(domain)
    primary = index.get("primary")
    if not primary:
        return None
    items = index.get("items") or []
    item = next((row for row in items if isinstance(row, dict) and row.get("file") == primary), None)
    if not item:
        return None
    body_path = _domain_store_dir(domain) / str(item["file"])
    if not body_path.is_file():
        return None
    media_type = str(item.get("media_type") or "image/x-icon")
    return body_path, media_type


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


def persist_icon(
    domain: str,
    *,
    url: str,
    body: bytes,
    media_type: str,
    primary: bool,
) -> None:
    store = _domain_store_dir(domain)
    store.mkdir(parents=True, exist_ok=True)
    filename = f"{_file_key_for_url(url)}{_ext_for(media_type, url)}"
    (store / filename).write_bytes(body)

    index = load_index(domain)
    items = [row for row in index["items"] if isinstance(row, dict) and row.get("file") != filename]
    items.append({"file": filename, "url": url, "media_type": media_type})
    index["items"] = items
    if primary or not index.get("primary"):
        index["primary"] = filename
        _write_static_favicon(
            store,
            index,
            static_name=_static_filename(media_type, url),
            body=body,
        )
    _write_index(domain, index)
    if primary:
        _negative_cache.pop(domain, None)
        cache_set(domain, body, media_type)
