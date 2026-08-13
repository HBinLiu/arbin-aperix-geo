"""Doubao crawl credentials: DB account pool (P3) + file cold-start (P1)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoLoginExpired

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_storage_state_path(settings: Settings) -> Path | None:
    raw = (settings.doubao_crawl_storage_state_path or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_file() else None


def load_storage_state_from_file(settings: Settings) -> dict | None:
    """Load Playwright storage_state JSON for cold start. None if unset/missing."""
    path = resolve_storage_state_path(settings)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DoubaoCrawlError(f"invalid storage_state file: {path}") from exc
    if not isinstance(data, dict):
        raise DoubaoCrawlError(f"storage_state must be a JSON object: {path}")
    cookies = data.get("cookies")
    if not isinstance(cookies, list) or not cookies:
        raise DoubaoLoginExpired(f"storage_state has no cookies: {path}")
    return data


def save_storage_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def crawl_credentials_available(settings: Settings, db: Session | None = None) -> bool:
    """True when file cold-start or a fresh DB account exists."""
    if resolve_storage_state_path(settings) is not None:
        return True
    if db is None:
        return False
    try:
        from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO
        from aperix_geo.services.crawl_accounts.pool import count_fresh_active_accounts

        return count_fresh_active_accounts(db, platform=PLATFORM_DOUBAO, settings=settings) > 0
    except Exception:
        logger.debug("doubao account pool check failed", exc_info=True)
        return False
