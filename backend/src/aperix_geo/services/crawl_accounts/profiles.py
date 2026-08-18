"""Per-account Chromium user-data-dir (login, heartbeat, and crawl share one profile).

Doubao binds the session to a browser identity. The live session is this directory,
not a Cookie JSON copied into another Chrome.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def profile_root(*, explicit: str | None = None) -> Path:
    raw = (explicit if explicit is not None else os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip()
    if not raw:
        raise ValueError("GEO_CRAWL_PROFILE_ROOT is required for chrome profiles")
    return Path(raw)


def account_profile_dir(
    platform: str,
    account_id: Any,
    *,
    root: str | Path | None = None,
) -> Path:
    plat = _SAFE.sub("-", (platform or "doubao").strip().lower())[:32] or "doubao"
    aid = _SAFE.sub("", str(account_id or "").strip())
    if not aid:
        raise ValueError("account_id required for chrome profile path")
    base = Path(root) if root else profile_root()
    return base / plat / aid


def profile_is_ready(path: Path) -> bool:
    """True when Chromium has written a real user profile (not an empty mount)."""
    if not path.is_dir():
        return False
    if (path / "Default").is_dir():
        return True
    if (path / "Cookies").is_file():
        return True
    return False


def job_account_fields(*, platform: str, account_id: Any | None) -> dict[str, str]:
    if account_id is None or str(account_id).strip() in ("", "0" * 32):
        return {}
    text = str(account_id).strip()
    if text in {"00000000-0000-0000-0000-000000000000"}:
        return {}
    plat = (platform or "doubao").strip().lower() or "doubao"
    return {"account_id": text, "platform": plat}


def job_uses_account_profile(payload: dict[str, Any]) -> bool:
    """True when geo-web-crawl should open this account's Chrome profile (no cookie inject)."""
    return bool(
        job_account_fields(
            platform=str(payload.get("platform") or ""),
            account_id=payload.get("account_id"),
        ).get("account_id")
    )
