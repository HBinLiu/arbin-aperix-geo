"""Doubao account pool: acquire / release / status updates."""

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
from aperix_geo.db.models import EPOCH, DoubaoAccount
from aperix_geo.services.doubao_accounts.session_cookies import storage_state_has_session_cookies

logger = logging.getLogger(__name__)

STATUS_ACTIVE = "active"
STATUS_NEED_RELOGIN = "need_relogin"
STATUS_LOGGING_IN = "logging_in"
STATUS_BLOCKED = "blocked"

# How many SKIP LOCKED candidates to try when rejecting empty/guest jars.
_ACQUIRE_ATTEMPTS = 8
# Extra seconds on top of crawl timeout so lease outlives a full sample.
_LEASE_TIMEOUT_BUFFER_S = 60


@dataclass(frozen=True)
class AccountLease:
    account_id: uuid.UUID
    label: str
    storage_state: dict[str, Any]
    lease_owner: str


def storage_state_has_cookies(state: dict[str, Any] | None) -> bool:
    """Alias kept for importers; requires session cookies (not guest-only)."""
    return storage_state_has_session_cookies(state)


def effective_account_lease_ttl_s(settings: Settings) -> int:
    """Lease must cover a full crawl wall-clock (+ buffer), not only the configured lease floor."""
    configured = int(settings.doubao_account_lease_ttl_s)
    crawl_need = int(math.ceil(float(settings.doubao_crawl_timeout_s))) + _LEASE_TIMEOUT_BUFFER_S
    return max(configured, crawl_need, 60)


def count_fresh_active_accounts(db: Session, *, settings: Settings | None = None) -> int:
    """Count active accounts that are fresh, unleased, and have session cookies."""
    settings = settings or get_settings()
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    rows = list(
        db.scalars(
            select(DoubaoAccount)
            .where(
                DoubaoAccount.status == STATUS_ACTIVE,
                DoubaoAccount.last_ok_at >= fresh_cutoff,
                DoubaoAccount.lease_until < now,
            )
            .order_by(DoubaoAccount.last_ok_at.desc())
            .limit(50)
        ).all()
    )
    return sum(1 for row in rows if storage_state_has_session_cookies(row.storage_state))


def acquire_account(
    db: Session,
    *,
    settings: Settings | None = None,
    lease_owner: str = "",
) -> AccountLease | None:
    """Take one fresh active account with row lock (SKIP LOCKED).

    Skips guest/empty jars (marks need_relogin + ticket) and tries the next candidate.
    """
    settings = settings or get_settings()
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    lease_ttl = effective_account_lease_ttl_s(settings)
    lease_until = now + timedelta(seconds=lease_ttl)
    owner = (lease_owner or "").strip() or str(uuid.uuid4())

    for _ in range(_ACQUIRE_ATTEMPTS):
        stmt = (
            select(DoubaoAccount)
            .where(
                DoubaoAccount.status == STATUS_ACTIVE,
                DoubaoAccount.last_ok_at >= fresh_cutoff,
                DoubaoAccount.lease_until < now,
            )
            .order_by(DoubaoAccount.last_ok_at.desc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = db.scalars(stmt).first()
        if row is None:
            return None
        if not storage_state_has_session_cookies(row.storage_state):
            row.status = STATUS_NEED_RELOGIN
            row.last_error = "storage_state missing Doubao session cookies"
            db.flush()
            from aperix_geo.services.doubao_accounts.human_ops import request_human_intervention

            request_human_intervention(
                db,
                account_id=row.id,
                reason="login_expired",
                error="storage_state missing Doubao session cookies",
                settings=settings,
            )
            # Try next candidate in the same transaction.
            continue

        row.lease_owner = owner
        row.lease_until = lease_until
        db.flush()
        return AccountLease(
            account_id=row.id,
            label=row.label,
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
    row = db.get(DoubaoAccount, account_id)
    if row is None:
        return
    if row.lease_owner and row.lease_owner != lease_owner:
        logger.warning(
            "doubao account lease owner mismatch id=%s expected=%s got=%s",
            account_id,
            row.lease_owner,
            lease_owner,
        )
        return

    row.lease_owner = ""
    row.lease_until = EPOCH
    if ok:
        if storage_state is not None and storage_state_has_session_cookies(storage_state):
            row.storage_state = storage_state
        elif storage_state is not None:
            # Successful crawl that somehow lost session cookies — force relogin.
            row.status = STATUS_NEED_RELOGIN
            row.last_error = "crawl ok but storage_state missing session cookies"
            logger.warning(
                "doubao account lost session cookies after crawl id=%s label=%s",
                row.id,
                row.label,
            )
            db.flush()
            return
        row.last_ok_at = utc_now()
        row.last_error = ""
        if row.status == STATUS_ACTIVE:
            pass
        elif row.status == STATUS_NEED_RELOGIN:
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
            logger.warning("doubao account need_relogin id=%s label=%s err=%s", row.id, row.label, message)
    db.flush()


def mark_need_relogin(
    db: Session,
    *,
    account_id: uuid.UUID,
    error: str = "",
    clear_lease: bool = True,
) -> None:
    """Mark account need_relogin.

    When ``clear_lease`` is False (e.g. heartbeat must not interrupt a live crawl),
    leave ``lease_owner`` / ``lease_until`` untouched.
    """
    row = db.get(DoubaoAccount, account_id)
    if row is None:
        return
    row.status = STATUS_NEED_RELOGIN
    if clear_lease:
        row.lease_owner = ""
        row.lease_until = EPOCH
    row.last_error = (error or "login expired").strip()[:2000]
    db.flush()
    logger.warning(
        "doubao account marked need_relogin id=%s label=%s clear_lease=%s",
        row.id,
        row.label,
        clear_lease,
    )


def upsert_account_from_state(
    db: Session,
    *,
    label: str,
    storage_state: dict[str, Any],
    status: str = STATUS_ACTIVE,
) -> DoubaoAccount:
    """Create or update a pool account (import / login ticket completion)."""
    if not storage_state_has_session_cookies(storage_state):
        raise ValueError("storage_state must include Doubao session cookies (sessionid / sid_guard / …)")
    name = (label or "").strip() or f"doubao-{uuid.uuid4().hex[:8]}"
    existing = db.scalars(
        select(DoubaoAccount).where(DoubaoAccount.label == name).limit(1)
    ).first()
    now = utc_now()
    if existing is None:
        row = DoubaoAccount(
            id=uuid.uuid4(),
            label=name,
            status=status,
            storage_state=storage_state,
            last_ok_at=now,
            last_error="",
            lease_owner="",
            lease_until=EPOCH,
        )
        db.add(row)
    else:
        row = existing
        row.storage_state = storage_state
        row.status = status
        row.last_ok_at = now
        row.last_error = ""
        row.lease_owner = ""
        row.lease_until = EPOCH
    db.flush()
    return row
