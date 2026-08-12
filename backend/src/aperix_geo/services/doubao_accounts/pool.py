"""Doubao account pool: acquire / release / status updates."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, DoubaoAccount

logger = logging.getLogger(__name__)

STATUS_ACTIVE = "active"
STATUS_NEED_RELOGIN = "need_relogin"
STATUS_LOGGING_IN = "logging_in"
STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class AccountLease:
    account_id: uuid.UUID
    label: str
    storage_state: dict[str, Any]
    lease_owner: str


def storage_state_has_cookies(state: dict[str, Any] | None) -> bool:
    if not isinstance(state, dict):
        return False
    cookies = state.get("cookies")
    return isinstance(cookies, list) and len(cookies) > 0


def count_fresh_active_accounts(db: Session, *, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    stmt = (
        select(DoubaoAccount.id)
        .where(
            DoubaoAccount.status == STATUS_ACTIVE,
            DoubaoAccount.last_ok_at >= fresh_cutoff,
        )
        .limit(50)
    )
    return len(list(db.scalars(stmt).all()))


def acquire_account(
    db: Session,
    *,
    settings: Settings | None = None,
    lease_owner: str = "",
) -> AccountLease | None:
    """Take one fresh active account with row lock (SKIP LOCKED)."""
    settings = settings or get_settings()
    now = utc_now()
    fresh_cutoff = now - timedelta(seconds=int(settings.doubao_heartbeat_fresh_s))
    lease_until = now + timedelta(seconds=int(settings.doubao_account_lease_ttl_s))
    owner = (lease_owner or "").strip() or str(uuid.uuid4())

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
    if not storage_state_has_cookies(row.storage_state):
        row.status = STATUS_NEED_RELOGIN
        row.last_error = "storage_state missing cookies"
        db.flush()
        return None

    row.lease_owner = owner
    row.lease_until = lease_until
    db.flush()
    return AccountLease(
        account_id=row.id,
        label=row.label,
        storage_state=dict(row.storage_state or {}),
        lease_owner=owner,
    )


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
        if storage_state is not None and storage_state_has_cookies(storage_state):
            row.storage_state = storage_state
        row.last_ok_at = utc_now()
        row.last_error = ""
        if row.status == STATUS_ACTIVE:
            pass
        elif row.status == STATUS_NEED_RELOGIN:
            # Successful crawl after relogin path — revive.
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


def mark_need_relogin(db: Session, *, account_id: uuid.UUID, error: str = "") -> None:
    row = db.get(DoubaoAccount, account_id)
    if row is None:
        return
    row.status = STATUS_NEED_RELOGIN
    row.lease_owner = ""
    row.lease_until = EPOCH
    row.last_error = (error or "login expired").strip()[:2000]
    db.flush()
    logger.warning("doubao account marked need_relogin id=%s label=%s", row.id, row.label)


def upsert_account_from_state(
    db: Session,
    *,
    label: str,
    storage_state: dict[str, Any],
    status: str = STATUS_ACTIVE,
) -> DoubaoAccount:
    """Create or update a pool account (import / login ticket completion)."""
    if not storage_state_has_cookies(storage_state):
        raise ValueError("storage_state must include cookies")
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
