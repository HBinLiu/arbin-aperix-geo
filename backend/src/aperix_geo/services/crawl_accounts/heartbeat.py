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
    account_session_ready,
    clear_account_lease,
    cookies_in_use,
    heartbeat_lease_ttl_s,
    pending_login_account_ids,
    release_account,
    try_lease_account,
)
from aperix_geo.services.crawl_accounts.cookies import (
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
    stale_before: datetime | None = None,
    now: datetime | None = None,
    limit: int = _HEARTBEAT_CHECK_LIMIT,
    pending_ticket_account_ids: set[UUID] | None = None,
    settings: Settings | None = None,
) -> list[CrawlAccount]:
    """Probe if the Chrome profile looks dead or last_ok_at is old. Skip VNC / ticket / lease."""
    settings = settings or Settings()
    now = now or utc_now()
    pending = pending_ticket_account_ids or set()
    if stale_before is None:
        stale_before = now - timedelta(
            seconds=max(60, int(settings.doubao_heartbeat_fresh_s) // 2)
        )
    out: list[CrawlAccount] = []
    for row in rows:
        if cookies_in_use(row, now=now, pending_ids=pending):
            continue
        status = (row.status or "").strip()
        stale = status == STATUS_ACTIVE and row.last_ok_at < stale_before
        broken = status == STATUS_NEED_RELOGIN or not account_session_ready(
            row, settings=settings
        )
        if broken or stale:
            out.append(row)
        if len(out) >= limit:
            break
    return out


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
    plat = normalize_platform(platform)
    ops_sweep = {"expired": 0, "respawned": 0, "reopened": 0}
    if settings.doubao_ops_ticket_enabled:
        from aperix_geo.services.crawl_accounts.human_ops import sweep_stale_login_tickets

        ops_sweep = sweep_stale_login_tickets(db, platform=plat, settings=settings)
        db.commit()

    if not settings.doubao_heartbeat_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled", "ops_sweep": ops_sweep}
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
            "ops_sweep": ops_sweep,
        }

    now = utc_now()
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
    pending_ids = pending_login_account_ids(db, plat)
    rows = accounts_needing_heartbeat(
        pool_rows,
        now=now,
        pending_ticket_account_ids=pending_ids,
        settings=settings,
    )
    ttl_s = heartbeat_lease_ttl_s(settings)

    checked = 0
    revived = 0
    failed = 0
    skipped_busy = 0
    failures: list[dict[str, Any]] = []
    for row in rows:
        db.refresh(row)
        if cookies_in_use(row, now=utc_now(), pending_ids=pending_ids):
            skipped_busy += 1
            continue
        owner = f"heartbeat:{row.id.hex}"
        if not try_lease_account(db, account_id=row.id, lease_owner=owner, ttl_s=ttl_s):
            skipped_busy += 1
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
                dict(row.storage_state or {}),
                platform=plat,
                settings=settings,
                account_id=row.id,
            )
            cleaned = cookies_only_storage_state(new_state)
            writeback = (
                cleaned
                if storage_state_has_session_cookies(cleaned, platform=plat)
                else None
            )
            release_account(
                db,
                account_id=row.id,
                lease_owner=owner,
                storage_state=writeback,
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
        "skipped_leased": skipped_busy,
        "failures": failures,
        "ops_sweep": ops_sweep,
    }


def probe_account_login(
    storage_state: dict[str, Any],
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
    account_id: UUID | None = None,
) -> dict[str, Any]:
    """Open chat page with the account Chrome profile; raise if session unusable."""
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    if plat != PLATFORM_DOUBAO:
        raise DoubaoCrawlError(f"heartbeat probe not implemented for platform={plat}")
    if account_id is None and not storage_state_has_session_cookies(
        storage_state, platform=plat
    ):
        raise DoubaoLoginExpired(f"storage_state missing {plat} session cookies")
    if account_id is not None:
        root = (settings.geo_crawl_profile_root or "").strip()
        if root:
            from aperix_geo.services.crawl_accounts.profiles import (
                account_profile_dir,
                profile_is_ready,
            )

            profile_dir = account_profile_dir(plat, account_id, root=root)
            if not profile_is_ready(profile_dir):
                raise DoubaoLoginExpired(
                    f"chrome profile missing; noVNC login required dir={profile_dir}"
                )

    from aperix_geo.services.crawl_accounts.profiles import job_account_fields
    from aperix_geo.services.providers.doubao_web.jobs.probe import build_probe_payload

    payload = build_probe_payload(
        storage_state={"cookies": []} if account_id is not None else storage_state,
        settings=settings,
    )
    payload["platform"] = plat
    payload.update(job_account_fields(platform=plat, account_id=account_id))
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
        if account_id is not None:
            return {"cookies": []}
        raise DoubaoCrawlError("probe ok but storage_state missing")
    raise_from_job(job)
