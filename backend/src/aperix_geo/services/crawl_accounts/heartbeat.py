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
    storage_state_has_cookies,
)
from aperix_geo.services.crawl_accounts.session_cookies import cookies_only_storage_state
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)

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
        elif not storage_state_has_cookies(row.storage_state, platform=plat):
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

    checked = 0
    revived = 0
    failed = 0
    for row in rows:
        db.refresh(row)
        if _lease_active(row, now=utc_now()):
            continue
        checked += 1
        try:
            new_state = probe_account_login(
                row.storage_state, platform=plat, settings=settings
            )
            cleaned = cookies_only_storage_state(new_state)
            if not storage_state_has_cookies(cleaned, platform=plat):
                raise DoubaoLoginExpired(
                    "heartbeat probe returned storage_state without session cookies"
                )
            row.storage_state = cleaned
            row.last_ok_at = utc_now()
            row.last_error = ""
            # Probe success must return account to pool (sampling only acquires active).
            if row.status in (STATUS_NEED_RELOGIN, STATUS_LOGGING_IN):
                row.status = STATUS_ACTIVE
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
                "geo crawl heartbeat needs human ops id=%s label=%s platform=%s reason=%s",
                row.id,
                row.label,
                plat,
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
            logger.warning(
                "geo crawl heartbeat failed id=%s label=%s platform=%s: %s",
                row.id,
                row.label,
                plat,
                exc,
            )
        db.flush()

    db.commit()
    return {
        "ok": True,
        "skipped": False,
        "platform": plat,
        "checked": checked,
        "ok_count": revived,
        "failed": failed,
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
    if not storage_state_has_cookies(storage_state, platform=plat):
        raise DoubaoLoginExpired(f"storage_state missing {plat} session cookies")

    from aperix_geo.services.providers.doubao_web.jobs.probe import build_probe_payload
    from aperix_geo.services.geo_web_crawl.spawn import run_geo_web_crawl_spawn

    payload = build_probe_payload(storage_state=storage_state, settings=settings)
    payload["platform"] = plat
    timeout_s = float(payload.get("timeout_s") or 60)
    job = run_geo_web_crawl_spawn(
        payload,
        timeout_s=timeout_s,
        docker_image=(settings.geo_web_crawl_docker_image or "").strip(),
        base_url=(settings.geo_web_crawl_base_url or "").strip(),
        token=(settings.geo_web_crawl_token or "").strip(),
        mode="probe",
    )
    if job.get("ok"):
        state = job.get("storage_state")
        if isinstance(state, dict):
            return state
        raise DoubaoCrawlError("probe ok but storage_state missing")

    err_type = str(job.get("error_type") or "DoubaoCrawlError")
    err_msg = str(job.get("error") or "probe failed")
    if err_type == "DoubaoCaptchaRequired" or (
        job.get("human_ops") and "captcha" in err_msg.lower()
    ):
        raise DoubaoCaptchaRequired(err_msg)
    if err_type in {
        "DoubaoLoginExpired",
        "DoubaoNeedsHumanOps",
        "DoubaoCaptchaRequired",
    } or job.get("human_ops"):
        if err_type == "DoubaoCaptchaRequired":
            raise DoubaoCaptchaRequired(err_msg)
        if err_type == "DoubaoLoginExpired":
            raise DoubaoLoginExpired(err_msg)
        raise DoubaoNeedsHumanOps(err_msg)
    raise DoubaoCrawlError(f"{err_type}: {err_msg}")
