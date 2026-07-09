"""Embed sampling platform logos in brand reports."""

from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_ASSETS_DIR = _REPO_ROOT / "shared" / "assets" / "platform"

_PLATFORM_FILES: dict[str, str] = {
    "deepseek": "deepseek.png",
    "doubao": "doubao.png",
    "yuanbao": "yuanbao.png",
    "kimi": "kimi.png",
    "ernie": "ernie.png",
    "qianwen": "qianwen.png",
}


@lru_cache(maxsize=32)
def platform_logo_data_url(platform_key: str) -> str | None:
    """Return a ``data:`` URI for a known platform logo, or ``None``."""
    filename = _PLATFORM_FILES.get(platform_key.strip())
    if not filename:
        return None
    path = _ASSETS_DIR / filename
    if not path.is_file():
        return None
    body = path.read_bytes()
    media_type = mimetypes.guess_type(filename)[0] or "image/png"
    encoded = base64.b64encode(body).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
