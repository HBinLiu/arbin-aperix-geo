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
from aperix_geo.db.models import EPOCH, ZERO_UUID, CrawlAccount, CrawlLoginTicket
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform
from aperix_geo.services.crawl_accounts.cookies import (
    cookies_only_storage_state,
    storage_state_has_session_cookies,
)

logger = logging.getLogger(__name__)

STATUS_ACTIVE = "active"
STATUS_NEED_RELOGIN = "need_relogin"
STATUS_LOGGING_IN = "logging_in"
STATUS_BLOCKED = "blocked"

LEASE_OWNER_OPS_HANDOFF = "ops-handoff"

_TICKET_PENDING = "pending"


def _lease_held(row: CrawlAccount, now) -> bool:
    return bool(row.lease_until and row.lease_until > now)


def pending_login_subquery(platform: str):
    """Account ids with an open login ticket (must not share the Chrome profile)."""
    plat = normalize_platform(platform)
    return select(CrawlLoginTicket.account_id).where(
        CrawlLoginTicket.platform == plat,
        CrawlLoginTicket.status == _TICKET_PENDING,
        CrawlLoginTicket.account_id != ZERO_UUID,
    )


def pending_login_account_ids(db: Session, platform: str) -> set[uuid.UUID]:
    return {aid for aid in db.scalars(pending_login_subquery(platform)).all() if aid}


def ensure_account_for_ops(
    db: Session,
    *,
    platform: str,
    label: str,
) -> CrawlAccount:
    """Get or create the pool row so a Chrome profile path can be keyed by account id."""
    plat = normalize_platform(platform)
    name = (label or "").strip() or f"{plat}-{uuid.uuid4().hex[:8]}"
    existing = db.scalars(
        select(CrawlAccount)
        .where(CrawlAccount.platform == plat, CrawlAccount.label == name)
        .limit(1)
    ).first()
    if existing is not None:
        return existing
    row = CrawlAccount(
        id=uuid.uuid4(),
        platform=plat,
        label=name,
        status=STATUS_LOGGING_IN,
        storage_state={"cookies": []},
        last_ok_at=EPOCH,
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    db.add(row)
    db.flush()
    return row


def list_accounts(
    db: Session,
    *,
    platform: str | None = None,
) -> list[CrawlAccount]:
    stmt = select(CrawlAccount).order_by(CrawlAccount.updated_at.desc()).limit(200)
    if platform is not None and str(platform).strip():
        stmt = stmt.where(CrawlAccount.platform == normalize_platform(platform))
    return list(db.scalars(stmt).all())


def account_to_dict(row: CrawlAccount) -> dict[str, Any]:
    cookies = row.storage_state.get("cookies") if isinstance(row.storage_state, dict) else None
    cookie_count = len(cookies) if isinstance(cookies, list) else 0
    return {
        "id": str(row.id),
        "platform": row.platform,
        "label": row.label,
        "status": row.status,
        "cookie_count": cookie_count,
        "last_ok_at": row.last_ok_at.isoformat(),
        "last_error": row.last_error,
        "lease_owner": row.lease_owner,
        "lease_until": row.lease_until.isoformat(),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def apply_ops_handoff_lease(
    row: CrawlAccount,
    *,
    settings: Settings | None = None,
) -> None:
    """Block acquire/heartbeat until the noVNC Chromium is gone from Doubao's side."""
    settings = settings or get_settings()
    handoff_s = int(settings.doubao_ops_handoff_s or 0)
    if handoff_s <= 0:
        return
    row.lease_owner = LEASE_OWNER_OPS_HANDOFF
    row.lease_until = utc_now() + timedelta(seconds=handoff_s)
    logger.warning(
        "crawl login handoff lease id=%s label=%s until=%s s=%s",
        row.id,
        row.label,
        row.lease_until.isoformat(),
        handoff_s,
    )


def cookies_in_use(row: CrawlAccount, *, now, pending_ids: set[uuid.UUID]) -> bool:
    """True if a login ticket or crawl/heartbeat lease holds this account."""
    if (row.status or "").strip() == STATUS_LOGGING_IN:
        return True
    if row.id in pending_ids:
        return True
    return _lease_held(row, now)


_ACQUIRE_ATTEMPTS = 8
_LEASE_TIMEOUT_BUFFER_S = 60
_HEARTBEAT_LEASE_BUFFER_S = 30


@dataclass(frozen=True)
class AccountLease:
    account_id: uuid.UUID
    label: str
    platform: str
    storage_state: dict[str, Any]
    lease_owner: str


def effective_account_lease_ttl_s(settings: Settings) -> int:
    configured = int(settings.doubao_account_lease_ttl_s)
    crawl_need = int(math.ceil(float(settings.doubao_crawl_timeout_s))) + _LEASE_TIMEOUT_BUFFER_S
    return max(configured, crawl_need, 60)


def heartbeat_lease_ttl_s(settings: Settings) -> int:
    """Cover probe timeout + send wait; sampling must not acquire mid-probe."""
    probe_s = min(90.0, float(settings.doubao_crawl_timeout_s))
    send_wait = float(settings.doubao_heartbeat_send_wait_s)
    return max(60, int(math.ceil(probe_s + send_wait + _HEARTBEAT_LEASE_BUFFER_S)))


def count_fresh_active_accounts(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    snap = account_pool_capacity_snapshot(db, platform=platform, settings=settings)
    return snap["free"]


def account_session_ready(row: CrawlAccount, *, settings: Settings) -> bool:
    """True when this row can be leased without opening a login ticket.

    Production (``GEO_CRAWL_PROFILE_ROOT``): Chromium profile on disk is the session.
    Local smoke (no root): DB session cookies.
    """
    plat = normalize_platform(row.platform)
    root = (settings.geo_crawl_profile_root or "").strip()
    if root:
        from aperix_geo.services.crawl_accounts.profiles import (
            account_profile_dir,
            profile_is_ready,
        )

        return profile_is_ready(account_profile_dir(plat, row.id, root=root))
    return storage_state_has_session_cookies(row.storage_state, platform=plat)


def _acquire_not_ready_error(row: CrawlAccount, *, settings: Settings) -> str:
    plat = normalize_platform(row.platform)
    root = (settings.geo_crawl_profile_root or "").strip()
    if root:
        from aperix_geo.services.crawl_accounts.profiles import account_profile_dir

        profile_dir = account_profile_dir(plat, row.id, root=root)
        return f"chrome profile missing; noVNC login required dir={profile_dir}"
    return f"storage_state missing {plat} session cookies"


def account_pool_capacity_snapshot(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Fresh active accounts that can be leased: free vs busy."""
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
        if not account_session_ready(row, settings=settings):
            continue
        if _lease_held(row, now):
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
                CrawlAccount.id.notin_(pending_login_subquery(plat)),
            )
            .order_by(CrawlAccount.last_ok_at.desc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = db.scalars(stmt).first()
        if row is None:
            return None
        if not account_session_ready(row, settings=settings):
            row.status = STATUS_NEED_RELOGIN
            row.last_error = _acquire_not_ready_error(row, settings=settings)
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


def try_lease_account(
    db: Session,
    *,
    account_id: uuid.UUID,
    lease_owner: str,
    ttl_s: int,
) -> bool:
    """Take a short lease on a specific row if it is currently free.

    Used by heartbeat so sampling cannot acquire the same account mid-probe.
    ``skip_locked``: another worker already inspecting this row → treat as busy.
    """
    now = utc_now()
    owner = (lease_owner or "").strip()
    if not owner:
        return False
    stmt = (
        select(CrawlAccount)
        .where(CrawlAccount.id == account_id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    row = db.scalars(stmt).first()
    if row is None:
        return False
    if row.lease_until and row.lease_until > now:
        return False
    row.lease_owner = owner
    row.lease_until = now + timedelta(seconds=max(60, int(ttl_s)))
    db.flush()
    return True


def clear_account_lease(
    db: Session,
    *,
    account_id: uuid.UUID,
    lease_owner: str,
) -> None:
    """Drop a lease without touching cookies / last_ok_at / status."""
    row = db.get(CrawlAccount, account_id)
    if row is None:
        return
    if row.lease_owner and row.lease_owner != lease_owner:
        logger.warning(
            "geo crawl account lease owner mismatch on clear id=%s expected=%s got=%s",
            account_id,
            row.lease_owner,
            lease_owner,
        )
        return
    row.lease_owner = ""
    row.lease_until = EPOCH
    db.flush()


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
            # Successful crawl + empty CDP export must not evict a working account.
            logger.warning(
                "geo crawl account export lost session cookies after ok crawl; "
                "keeping previous jar id=%s label=%s platform=%s",
                row.id,
                row.label,
                plat,
            )
        row.last_ok_at = utc_now()
        row.last_error = ""
        if row.status == STATUS_NEED_RELOGIN:
            row.status = STATUS_ACTIVE
    else:
        # Generic fail keeps status. Login/captcha must go through human_ops
        # (typed job envelope), not substring matching on error text.
        row.last_error = (error or "crawl failed").strip()[:2000]
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
