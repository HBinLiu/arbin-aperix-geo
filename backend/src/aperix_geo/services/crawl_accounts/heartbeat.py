"""Geo crawl account heartbeat (real login proof via short send + cookie refresh)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import CrawlAccount
from aperix_geo.services.crawl_accounts.human_ops import request_human_intervention
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform
from aperix_geo.services.crawl_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_LOGGING_IN,
    STATUS_NEED_RELOGIN,
    clear_account_lease,
    heartbeat_lease_ttl_s,
    release_account,
    try_lease_account,
)
from aperix_geo.services.crawl_accounts.session_cookies import (
    cookies_only_storage_state,
    session_cookie_names,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.runtime import raise_from_job, spawn_doubao_job

logger = logging.getLogger(__name__)

_HEARTBEAT_SCAN_LIMIT = 100
_HEARTBEAT_CHECK_LIMIT = 20


def _lease_active(row: CrawlAccount, *, now: datetime) -> bool:
    return bool(row.lease_until and row.lease_until > now)


def in_sampling_heartbeat_quiet_window(
    settings: Settings,
    *,
    now: datetime | None = None,
) -> bool:
    """True during Beijing SAMPLING_DAILY_* enqueue window (auto-heartbeat should idle)."""
    from zoneinfo import ZoneInfo

    from aperix_geo.services.sampling.workflow.schedule import (
        SAMPLING_TIMEZONE,
        is_within_sampling_enqueue_window,
    )

    local_now = (now or utc_now()).astimezone(ZoneInfo(SAMPLING_TIMEZONE))
    return is_within_sampling_enqueue_window(local_now, settings=settings)


def accounts_needing_heartbeat(
    rows: list[CrawlAccount],
    *,
    stale_before: datetime,
    now: datetime | None = None,
    limit: int = _HEARTBEAT_CHECK_LIMIT,
) -> list[CrawlAccount]:
    now = now or utc_now()
    priority: list[CrawlAccount] = []
    stale: list[CrawlAccount] = []
    for row in rows:
        if _lease_active(row, now=now):
            continue
        plat = normalize_platform(row.platform)
        status = (row.status or "").strip()
        if status in (STATUS_NEED_RELOGIN, STATUS_LOGGING_IN):
            priority.append(row)
        elif not storage_state_has_session_cookies(row.storage_state, platform=plat):
            priority.append(row)
        elif status == STATUS_ACTIVE and row.last_ok_at < stale_before:
            stale.append(row)
    selected: list[CrawlAccount] = []
    seen: set[UUID] = set()
    for row in priority + stale:
        if row.id in seen:
            continue
        seen.add(row.id)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def run_crawl_account_heartbeat(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
    respect_sampling_quiet: bool = True,
) -> dict[str, Any]:
    """Probe pool accounts for one platform; on failure open human ticket + alert.

    Celery Beat keeps ``respect_sampling_quiet=True`` and always skips during the
    daily sampling enqueue window (``SAMPLING_DAILY_HOUR`` + window minutes).
    Manual ``crawl_heartbeat_run.py`` passes ``respect_sampling_quiet=False``.
    """
    settings = settings or get_settings()
    if not settings.doubao_heartbeat_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled"}
    if respect_sampling_quiet and in_sampling_heartbeat_quiet_window(settings):
        logger.info(
            "crawl heartbeat skipped reason=sampling_window "
            "daily_hour=%s window_min=%s",
            settings.sampling_daily_hour,
            settings.sampling_daily_window_minutes,
        )
        return {
            "ok": True,
            "skipped": True,
            "reason": "sampling_window",
            "sampling_daily_hour": settings.sampling_daily_hour,
            "sampling_daily_window_minutes": settings.sampling_daily_window_minutes,
        }

    plat = normalize_platform(platform)
    now = utc_now()
    stale_before = now - timedelta(seconds=max(60, int(settings.doubao_heartbeat_fresh_s) // 2))
    pool_rows = list(
        db.scalars(
            select(CrawlAccount)
            .where(
                CrawlAccount.platform == plat,
                CrawlAccount.status.in_(
                    (STATUS_ACTIVE, STATUS_NEED_RELOGIN, STATUS_LOGGING_IN)
                ),
            )
            .order_by(CrawlAccount.updated_at.asc())
            .limit(_HEARTBEAT_SCAN_LIMIT)
        ).all()
    )
    rows = accounts_needing_heartbeat(pool_rows, stale_before=stale_before, now=now)
    ttl_s = heartbeat_lease_ttl_s(settings)

    checked = 0
    revived = 0
    failed = 0
    skipped_leased = 0
    failures: list[dict[str, Any]] = []
    for row in rows:
        db.refresh(row)
        if _lease_active(row, now=utc_now()):
            skipped_leased += 1
            continue
        owner = f"heartbeat:{row.id.hex}"
        if not try_lease_account(db, account_id=row.id, lease_owner=owner, ttl_s=ttl_s):
            skipped_leased += 1
            db.commit()
            continue
        db.commit()
        checked += 1
        logger.info(
            "geo crawl heartbeat probe id=%s label=%s platform=%s status=%s "
            "session_cookies=%s",
            row.id,
            row.label,
            plat,
            row.status,
            session_cookie_names(row.storage_state, platform=plat),
        )
        try:
            new_state = probe_account_login(
                dict(row.storage_state or {}), platform=plat, settings=settings
            )
            cleaned = cookies_only_storage_state(new_state)
            if not storage_state_has_session_cookies(cleaned, platform=plat):
                raise DoubaoLoginExpired(
                    "heartbeat probe returned storage_state without session cookies"
                )
            release_account(
                db,
                account_id=row.id,
                lease_owner=owner,
                storage_state=cleaned,
                ok=True,
            )
            db.refresh(row)
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
            failures.append(
                {
                    "id": str(row.id),
                    "label": row.label,
                    "reason": reason,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            logger.warning(
                "geo crawl heartbeat needs human ops id=%s label=%s platform=%s "
                "reason=%s err=%s",
                row.id,
                row.label,
                plat,
                reason,
                str(exc)[:400],
            )
        except DoubaoCrawlError as exc:
            row.last_error = str(exc)[:2000]
            if exc.session_alive:
                # Logged-in DOM / send flake: keep the account rentable.
                row.last_ok_at = utc_now()
            clear_account_lease(db, account_id=row.id, lease_owner=owner)
            failed += 1
            failures.append(
                {
                    "id": str(row.id),
                    "label": row.label,
                    "reason": "probe_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                    "session_alive": bool(exc.session_alive),
                }
            )
            logger.warning(
                "geo crawl heartbeat probe error (keep cookies) id=%s label=%s "
                "platform=%s session_alive=%s err=%s",
                row.id,
                row.label,
                plat,
                exc.session_alive,
                exc,
            )
        except Exception as exc:
            row.last_error = str(exc)[:2000]
            clear_account_lease(db, account_id=row.id, lease_owner=owner)
            failed += 1
            failures.append(
                {
                    "id": str(row.id),
                    "label": row.label,
                    "reason": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            logger.warning(
                "geo crawl heartbeat failed id=%s label=%s platform=%s: %s",
                row.id,
                row.label,
                plat,
                exc,
            )
        db.commit()

    return {
        "ok": True,
        "skipped": False,
        "platform": plat,
        "checked": checked,
        "ok_count": revived,
        "failed": failed,
        "skipped_leased": skipped_leased,
        "failures": failures,
    }


def probe_account_login(
    storage_state: dict[str, Any],
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Open chat page with storage_state; raise DoubaoNeedsHumanOps if session unusable."""
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    if plat != PLATFORM_DOUBAO:
        raise DoubaoCrawlError(f"heartbeat probe not implemented for platform={plat}")
    if not storage_state_has_session_cookies(storage_state, platform=plat):
        raise DoubaoLoginExpired(f"storage_state missing {plat} session cookies")

    from aperix_geo.services.providers.doubao_web.jobs.probe import build_probe_payload

    payload = build_probe_payload(storage_state=storage_state, settings=settings)
    payload["platform"] = plat
    job = spawn_doubao_job(
        payload,
        settings=settings,
        mode="probe",
        timeout_s=float(payload.get("timeout_s") or 60),
    )
    if job.get("ok"):
        state = job.get("storage_state")
        if isinstance(state, dict):
            return state
        raise DoubaoCrawlError("probe ok but storage_state missing")
    raise_from_job(job)
