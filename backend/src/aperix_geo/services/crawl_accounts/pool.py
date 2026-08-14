"""Geo crawl account pool: acquire / release / status updates (per platform)."""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, CrawlAccount
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform
from aperix_geo.services.crawl_accounts.session_cookies import (
    cookies_only_storage_state,
    storage_state_has_session_cookies,
)

logger = logging.getLogger(__name__)

STATUS_ACTIVE = "active"
STATUS_NEED_RELOGIN = "need_relogin"
STATUS_LOGGING_IN = "logging_in"
STATUS_BLOCKED = "blocked"

_ACQUIRE_ATTEMPTS = 8
_LEASE_TIMEOUT_BUFFER_S = 60


@dataclass(frozen=True)
class AccountLease:
    account_id: uuid.UUID
    label: str
    platform: str
    storage_state: dict[str, Any]
    lease_owner: str


def storage_state_has_cookies(
    state: dict[str, Any] | None,
    *,
    platform: str = PLATFORM_DOUBAO,
) -> bool:
    return storage_state_has_session_cookies(state, platform=platform)


def effective_account_lease_ttl_s(settings: Settings) -> int:
    configured = int(settings.doubao_account_lease_ttl_s)
    crawl_need = int(math.ceil(float(settings.doubao_crawl_timeout_s))) + _LEASE_TIMEOUT_BUFFER_S
    return max(configured, crawl_need, 60)


def count_fresh_active_accounts(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    snap = account_pool_capacity_snapshot(db, platform=platform, settings=settings)
    return snap["free"]


def account_pool_capacity_snapshot(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Fresh active accounts with session cookies: free (acquirable) vs leased (busy)."""
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    rows = list(
        db.scalars(
            select(CrawlAccount)
            .where(
                CrawlAccount.platform == plat,
                CrawlAccount.status == STATUS_ACTIVE,
                CrawlAccount.last_ok_at >= fresh_cutoff,
            )
            .order_by(CrawlAccount.last_ok_at.desc())
            .limit(50)
        ).all()
    )
    free = 0
    leased = 0
    for row in rows:
        if not storage_state_has_session_cookies(row.storage_state, platform=plat):
            continue
        if row.lease_until and row.lease_until > now:
            leased += 1
        else:
            free += 1
    return {"free": free, "leased": leased, "total": free + leased}


def acquire_account(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
    lease_owner: str = "",
) -> AccountLease | None:
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    lease_ttl = effective_account_lease_ttl_s(settings)
    lease_until = now + timedelta(seconds=lease_ttl)
    owner = (lease_owner or "").strip() or str(uuid.uuid4())

    for _ in range(_ACQUIRE_ATTEMPTS):
        stmt = (
            select(CrawlAccount)
            .where(
                CrawlAccount.platform == plat,
                CrawlAccount.status == STATUS_ACTIVE,
                CrawlAccount.last_ok_at >= fresh_cutoff,
                CrawlAccount.lease_until < now,
            )
            .order_by(CrawlAccount.last_ok_at.desc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = db.scalars(stmt).first()
        if row is None:
            return None
        if not storage_state_has_session_cookies(row.storage_state, platform=plat):
            row.status = STATUS_NEED_RELOGIN
            row.last_error = f"storage_state missing {plat} session cookies"
            db.flush()
            from aperix_geo.services.crawl_accounts.human_ops import request_human_intervention

            request_human_intervention(
                db,
                account_id=row.id,
                reason="login_expired",
                error=row.last_error,
                settings=settings,
            )
            continue

        row.lease_owner = owner
        row.lease_until = lease_until
        db.flush()
        return AccountLease(
            account_id=row.id,
            label=row.label,
            platform=plat,
            storage_state=dict(row.storage_state or {}),
            lease_owner=owner,
        )
    return None


def release_account(
    db: Session,
    *,
    account_id: uuid.UUID,
    lease_owner: str,
    storage_state: dict[str, Any] | None = None,
    ok: bool = True,
    error: str = "",
) -> None:
    row = db.get(CrawlAccount, account_id)
    if row is None:
        return
    plat = normalize_platform(row.platform)
    if row.lease_owner and row.lease_owner != lease_owner:
        logger.warning(
            "geo crawl account lease owner mismatch id=%s expected=%s got=%s",
            account_id,
            row.lease_owner,
            lease_owner,
        )
        return

    row.lease_owner = ""
    row.lease_until = EPOCH
    if ok:
        if storage_state is not None and storage_state_has_session_cookies(
            storage_state, platform=plat
        ):
            row.storage_state = cookies_only_storage_state(storage_state)
        elif storage_state is not None:
            row.status = STATUS_NEED_RELOGIN
            row.last_error = "crawl ok but storage_state missing session cookies"
            logger.warning(
                "geo crawl account lost session cookies after crawl id=%s label=%s platform=%s",
                row.id,
                row.label,
                plat,
            )
            db.flush()
            return
        row.last_ok_at = utc_now()
        row.last_error = ""
        if row.status == STATUS_NEED_RELOGIN:
            row.status = STATUS_ACTIVE
    else:
        message = (error or "crawl failed").strip()
        row.last_error = message[:2000]
        if (
            "login" in message.lower()
            or "登录" in message
            or "captcha" in message.lower()
            or "验证码" in message
            or "人机验证" in message
            or "行为验证" in message
        ):
            row.status = STATUS_NEED_RELOGIN
            logger.warning(
                "geo crawl account need_relogin id=%s label=%s platform=%s err=%s",
                row.id,
                row.label,
                plat,
                message,
            )
    db.flush()


def mark_need_relogin(
    db: Session,
    *,
    account_id: uuid.UUID,
    error: str = "",
    clear_lease: bool = True,
) -> None:
    row = db.get(CrawlAccount, account_id)
    if row is None:
        return
    row.status = STATUS_NEED_RELOGIN
    if clear_lease:
        row.lease_owner = ""
        row.lease_until = EPOCH
    row.last_error = (error or "login expired").strip()[:2000]
    db.flush()
    logger.warning(
        "geo crawl account marked need_relogin id=%s label=%s platform=%s clear_lease=%s",
        row.id,
        row.label,
        row.platform,
        clear_lease,
    )


def upsert_account_from_state(
    db: Session,
    *,
    label: str,
    storage_state: dict[str, Any],
    platform: str = PLATFORM_DOUBAO,
    status: str = STATUS_ACTIVE,
) -> CrawlAccount:
    plat = normalize_platform(platform)
    if not storage_state_has_session_cookies(storage_state, platform=plat):
        raise ValueError(f"storage_state must include {plat} session cookies")
    slim = cookies_only_storage_state(storage_state)
    name = (label or "").strip() or f"{plat}-{uuid.uuid4().hex[:8]}"
    existing = db.scalars(
        select(CrawlAccount)
        .where(CrawlAccount.platform == plat, CrawlAccount.label == name)
        .limit(1)
    ).first()
    now = utc_now()
    if existing is None:
        row = CrawlAccount(
            id=uuid.uuid4(),
            platform=plat,
            label=name,
            status=status,
            storage_state=slim,
            last_ok_at=now,
            last_error="",
            lease_owner="",
            lease_until=EPOCH,
        )
        db.add(row)
    else:
        row = existing
        row.storage_state = slim
        row.status = status
        row.last_ok_at = now
        row.last_error = ""
        row.lease_owner = ""
        row.lease_until = EPOCH
    db.flush()
    return row
