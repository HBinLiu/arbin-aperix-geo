"""Lightweight Doubao account heartbeat (login probe + cookie refresh)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import DoubaoAccount
from aperix_geo.services.doubao_accounts.human_ops import request_human_intervention
from aperix_geo.services.doubao_accounts.pool import (
    STATUS_ACTIVE,
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


def run_doubao_account_heartbeat(
    db: Session,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Probe active accounts; on failure open human ticket + alert. No-op when disabled."""
    settings = settings or get_settings()
    if not settings.doubao_heartbeat_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled"}

    now = utc_now()
    # Heartbeat accounts that are active and either stale or due soon.
    stale_before = now - timedelta(seconds=max(60, int(settings.doubao_heartbeat_fresh_s) // 2))
    rows = list(
        db.scalars(
            select(DoubaoAccount)
            .where(
                DoubaoAccount.status == STATUS_ACTIVE,
                DoubaoAccount.last_ok_at < stale_before,
            )
            .order_by(DoubaoAccount.last_ok_at.asc())
            .limit(20)
        ).all()
    )

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
