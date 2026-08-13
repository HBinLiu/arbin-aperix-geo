"""Lightweight Doubao account heartbeat (login probe + cookie refresh)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import DoubaoAccount
from aperix_geo.services.doubao_accounts.human_ops import request_human_intervention
from aperix_geo.services.doubao_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_LOGGING_IN,
    STATUS_NEED_RELOGIN,
    storage_state_has_cookies,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha

logger = logging.getLogger(__name__)

_HEARTBEAT_SCAN_LIMIT = 100
_HEARTBEAT_CHECK_LIMIT = 20


def accounts_needing_heartbeat(
    rows: list[DoubaoAccount],
    *,
    stale_before: datetime,
    limit: int = _HEARTBEAT_CHECK_LIMIT,
) -> list[DoubaoAccount]:
    """Always include need_relogin / logging_in / empty-cookie; then stale actives."""
    priority: list[DoubaoAccount] = []
    stale: list[DoubaoAccount] = []
    for row in rows:
        status = (row.status or "").strip()
        if status in (STATUS_NEED_RELOGIN, STATUS_LOGGING_IN):
            priority.append(row)
        elif not storage_state_has_cookies(row.storage_state):
            priority.append(row)
        elif status == STATUS_ACTIVE and row.last_ok_at < stale_before:
            stale.append(row)
    selected: list[DoubaoAccount] = []
    seen: set[UUID] = set()
    for row in priority + stale:
        if row.id in seen:
            continue
        seen.add(row.id)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def run_doubao_account_heartbeat(
    db: Session,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Probe pool accounts; on failure open human ticket + alert. No-op when disabled."""
    settings = settings or get_settings()
    if not settings.doubao_heartbeat_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled"}

    now = utc_now()
    # Stale ≈ half the sampling freshness window.
    # need_relogin / logging_in / empty-cookie actives are always candidates (else no new tickets).
    stale_before = now - timedelta(seconds=max(60, int(settings.doubao_heartbeat_fresh_s) // 2))
    pool_rows = list(
        db.scalars(
            select(DoubaoAccount)
            .where(
                DoubaoAccount.status.in_(
                    (STATUS_ACTIVE, STATUS_NEED_RELOGIN, STATUS_LOGGING_IN)
                )
            )
            .order_by(DoubaoAccount.updated_at.asc())
            .limit(_HEARTBEAT_SCAN_LIMIT)
        ).all()
    )
    rows = accounts_needing_heartbeat(pool_rows, stale_before=stale_before)

    checked = 0
    revived = 0
    failed = 0
    for row in rows:
        checked += 1
        try:
            new_state = probe_account_login(row.storage_state, settings=settings)
            row.storage_state = new_state
            row.last_ok_at = utc_now()
            row.last_error = ""
            revived += 1
        except DoubaoNeedsHumanOps as exc:
            reason = "captcha" if isinstance(exc, DoubaoCaptchaRequired) else "login_expired"
            request_human_intervention(
                db,
                account_id=row.id,
                reason=reason,
                error=str(exc),
                settings=settings,
            )
            failed += 1
            logger.warning(
                "doubao heartbeat needs human ops id=%s label=%s reason=%s",
                row.id,
                row.label,
                reason,
            )
        except Exception as exc:
            request_human_intervention(
                db,
                account_id=row.id,
                reason="login_expired",
                error=str(exc),
                settings=settings,
            )
            failed += 1
            logger.warning("doubao heartbeat failed id=%s label=%s: %s", row.id, row.label, exc)
        db.flush()

    db.commit()
    return {
        "ok": True,
        "skipped": False,
        "checked": checked,
        "ok_count": revived,
        "failed": failed,
    }


def probe_account_login(
    storage_state: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Open chat page with storage_state; raise DoubaoNeedsHumanOps if session unusable."""
    settings = settings or get_settings()
    if not storage_state_has_cookies(storage_state):
        raise DoubaoLoginExpired("storage_state missing cookies")

    try:
        from aperix_geo.services.providers.doubao_web.browser import browser_page_session
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    base_url = (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_ms = min(60_000, int(settings.doubao_crawl_timeout_s * 1000))

    with browser_page_session(settings, storage_state=storage_state) as (page, context):
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        url = (page.url or "").lower()
        if "login" in url or "passport" in url:
            raise DoubaoLoginExpired(f"redirected to login: {page.url}")
        try:
            body = page.locator("body").inner_text(timeout=3_000) or ""
        except Exception:
            body = ""
        if page_looks_like_captcha(body):
            raise DoubaoCaptchaRequired("behavior captcha on heartbeat probe")
        for css in sel.CAPTCHA_DOM_SELECTORS:
            try:
                loc = page.locator(css)
                if loc.count() > 0 and loc.first.is_visible():
                    raise DoubaoCaptchaRequired("behavior captcha on heartbeat probe")
            except DoubaoCaptchaRequired:
                raise
            except Exception:
                continue
        login_btn = page.get_by_role("button", name=sel.LOGIN_HINT)
        composer = page.locator("textarea, div[contenteditable='true']")
        if login_btn.count() > 0 and composer.count() == 0:
            raise DoubaoLoginExpired("login UI visible")
        if composer.count() == 0:
            raise DoubaoLoginExpired("chat composer not found")
        return context.storage_state()
