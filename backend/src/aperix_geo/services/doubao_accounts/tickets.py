"""Doubao account tickets: create / complete / cancel (geo-crawl-ops noVNC or upload)."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, ZERO_UUID, DoubaoAccount, DoubaoLoginTicket
from aperix_geo.services.doubao_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_LOGGING_IN,
    STATUS_NEED_RELOGIN,
    upsert_account_from_state,
)
from aperix_geo.services.geo_crawl_ops import (
    GeoCrawlOpsDockerError,
    geo_crawl_ops_ready,
    ops_session_running,
    spawn_ops_session,
    stop_ops_session,
)
from aperix_geo.services.providers.doubao_web import selectors as sel

logger = logging.getLogger(__name__)

TICKET_PENDING = "pending"
TICKET_SUCCEEDED = "succeeded"
TICKET_FAILED = "failed"
TICKET_EXPIRED = "expired"
TICKET_CANCELLED = "cancelled"

PLATFORM = "doubao"

# Strong login signals (same set as scripts/doubao_web_login.py). Guest cookies like odin_tt do not count.
_SESSION_COOKIE_NAMES = frozenset(
    {
        "sessionid",
        "sessionid_ss",
        "sid_guard",
        "sid_tt",
        "uid_tt",
        "uid_tt_ss",
    }
)


def novnc_configured(settings: Settings | None = None) -> bool:
    """Doubao tickets can use shared geo-crawl-ops noVNC when ticket flag + GEO_CRAWL_OPS_* are set."""
    settings = settings or get_settings()
    return bool(settings.doubao_ops_ticket_enabled and geo_crawl_ops_ready(settings))


def _expire_if_needed(ticket: DoubaoLoginTicket) -> bool:
    if ticket.status != TICKET_PENDING:
        return False
    if ticket.expires_at <= utc_now():
        ticket.status = TICKET_EXPIRED
        ticket.error_text = "ticket expired"
        if (ticket.container_id or "").strip():
            stop_ops_session(ticket.container_id)
            ticket.container_id = ""
            ticket.login_url = ""
        return True
    return False


def list_accounts(db: Session) -> list[DoubaoAccount]:
    return list(
        db.scalars(
            select(DoubaoAccount).order_by(DoubaoAccount.updated_at.desc()).limit(200)
        ).all()
    )


def account_to_dict(row: DoubaoAccount) -> dict[str, Any]:
    cookies = row.storage_state.get("cookies") if isinstance(row.storage_state, dict) else None
    cookie_count = len(cookies) if isinstance(cookies, list) else 0
    return {
        "id": str(row.id),
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


def ticket_to_dict(ticket: DoubaoLoginTicket, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "id": str(ticket.id),
        "account_id": str(ticket.account_id),
        "label": ticket.label,
        "token": ticket.token,
        "status": ticket.status,
        "operator": ticket.operator,
        "login_url": ticket.login_url,
        "novnc_available": bool(ticket.login_url.strip()),
        "upload_fallback": not bool(ticket.login_url.strip()),
        "container_id": ticket.container_id,
        "expires_at": ticket.expires_at.isoformat(),
        "completed_at": ticket.completed_at.isoformat(),
        "error_text": ticket.error_text,
        "created_at": ticket.created_at.isoformat(),
    }


def create_login_ticket(
    db: Session,
    *,
    label: str = "",
    account_id: UUID | None = None,
    operator: str = "",
    reason: str = "login_expired",
    settings: Settings | None = None,
) -> DoubaoLoginTicket:
    settings = settings or get_settings()
    if not settings.doubao_ops_ticket_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doubao ops tickets disabled (DOUBAO_OPS_TICKET_ENABLED=false)",
        )

    ops_reason = (reason or "login_expired").strip().lower()
    if ops_reason not in ("login_expired", "captcha"):
        ops_reason = "login_expired"

    account: DoubaoAccount | None = None
    resolved_label = (label or "").strip()
    resolved_account_id = ZERO_UUID
    storage_state: dict[str, Any] | None = None

    if account_id is not None and account_id != ZERO_UUID:
        account = db.get(DoubaoAccount, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        resolved_account_id = account.id
        resolved_label = account.label or resolved_label
        storage_state = dict(account.storage_state or {})
        account.status = STATUS_LOGGING_IN
        account.lease_owner = ""
        account.lease_until = EPOCH

    if not resolved_label:
        resolved_label = f"doubao-{uuid4().hex[:8]}"

    if resolved_account_id != ZERO_UUID:
        open_ticket = db.scalars(
            select(DoubaoLoginTicket)
            .where(
                DoubaoLoginTicket.account_id == resolved_account_id,
                DoubaoLoginTicket.status == TICKET_PENDING,
            )
            .limit(1)
        ).first()
        if open_ticket is not None:
            raise HTTPException(status_code=409, detail="Account already has a pending login ticket")

    ttl_min = int(settings.doubao_ops_ticket_ttl_min)
    ticket = DoubaoLoginTicket(
        id=uuid4(),
        account_id=resolved_account_id,
        label=resolved_label,
        token=secrets.token_urlsafe(24),
        status=TICKET_PENDING,
        operator=(operator or "").strip()[:128],
        login_url="",
        container_id="",
        expires_at=utc_now() + timedelta(minutes=ttl_min),
        completed_at=EPOCH,
        error_text="",
    )

    if novnc_configured(settings):
        _spawn_ops_onto_ticket(
            ticket,
            storage_state=storage_state,
            ops_reason=ops_reason,
            ttl_min=ttl_min,
            settings=settings,
        )
    else:
        ticket.error_text = "novnc_unavailable: complete via storage_state upload"

    db.add(ticket)
    db.flush()
    return ticket


def ensure_pending_ticket_session(
    db: Session,
    ticket: DoubaoLoginTicket,
    *,
    reason: str = "login_expired",
    settings: Settings | None = None,
) -> bool:
    """Keep a pending ticket usable: expire if due, else respawn dead noVNC.

    Returns True when a new ops container was started (caller should re-alert with
    the fresh login_url). Returns False when the existing session is still up,
    novnc is unavailable, or the ticket was expired.
    """
    settings = settings or get_settings()
    if _expire_if_needed(ticket):
        db.flush()
        return False
    if ticket.status != TICKET_PENDING:
        return False
    if not novnc_configured(settings):
        return False

    cid = (ticket.container_id or "").strip()
    if cid and ops_session_running(cid):
        return False

    ops_reason = (reason or "login_expired").strip().lower()
    if ops_reason not in ("login_expired", "captcha"):
        ops_reason = "login_expired"

    storage_state: dict[str, Any] | None = None
    if ticket.account_id != ZERO_UUID:
        account = db.get(DoubaoAccount, ticket.account_id)
        if account is not None:
            storage_state = dict(account.storage_state or {})
            if account.status != STATUS_LOGGING_IN:
                account.status = STATUS_LOGGING_IN

    if cid:
        stop_ops_session(cid)

    ttl_min = int(settings.doubao_ops_ticket_ttl_min)
    ticket.expires_at = utc_now() + timedelta(minutes=ttl_min)
    _spawn_ops_onto_ticket(
        ticket,
        storage_state=storage_state,
        ops_reason=ops_reason,
        ttl_min=ttl_min,
        settings=settings,
    )
    db.flush()
    logger.warning(
        "geo-crawl-ops session respawned for pending ticket=%s container=%s url=%s",
        ticket.id,
        (ticket.container_id or "")[:12],
        (ticket.login_url or "")[:80],
    )
    # True even if spawn fell back to upload — ops must be notified with current state.
    return True


def _spawn_ops_onto_ticket(
    ticket: DoubaoLoginTicket,
    *,
    storage_state: dict[str, Any] | None,
    ops_reason: str,
    ttl_min: int,
    settings: Settings,
) -> None:
    start_url = (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL
    try:
        session = spawn_ops_session(
            ticket_token=ticket.token,
            platform=PLATFORM,
            start_url=start_url,
            ttl_min=ttl_min,
            storage_state=storage_state,
            ops_reason=ops_reason,
            settings=settings,
        )
        ticket.container_id = session.container_id
        ticket.login_url = session.login_url
        ticket.error_text = (
            f"geo_crawl_ops_session: platform={PLATFORM} reason={ops_reason} "
            f"port={session.host_port} name={session.name}"
        )
    except GeoCrawlOpsDockerError as exc:
        logger.warning("geo-crawl-ops spawn failed; upload fallback ticket=%s: %s", ticket.id, exc)
        ticket.login_url = ""
        ticket.container_id = ""
        ticket.error_text = f"novnc_spawn_failed: {exc}; complete via storage_state upload"


def get_ticket(db: Session, ticket_id: UUID) -> DoubaoLoginTicket:
    ticket = db.get(DoubaoLoginTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if _expire_if_needed(ticket):
        db.flush()
    return ticket


def get_ticket_by_token(db: Session, token: str) -> DoubaoLoginTicket:
    tok = (token or "").strip()
    if not tok:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = db.scalars(
        select(DoubaoLoginTicket).where(DoubaoLoginTicket.token == tok).limit(1)
    ).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if _expire_if_needed(ticket):
        db.flush()
    return ticket


def session_cookie_names(storage_state: dict[str, Any]) -> list[str]:
    cookies = storage_state.get("cookies") if isinstance(storage_state, dict) else None
    if not isinstance(cookies, list):
        return []
    found: list[str] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "").strip()
        if name in _SESSION_COOKIE_NAMES and value:
            found.append(name)
    return sorted(set(found))


def require_session_storage_state(storage_state: dict[str, Any]) -> None:
    if not session_cookie_names(storage_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="storage_state missing Doubao session cookies (sessionid / sid_guard / uid_tt …)",
        )


def cancel_ticket(db: Session, ticket_id: UUID) -> DoubaoLoginTicket:
    ticket = get_ticket(db, ticket_id)
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")
    if (ticket.container_id or "").strip():
        stop_ops_session(ticket.container_id)
    ticket.status = TICKET_CANCELLED
    ticket.error_text = "cancelled"
    ticket.container_id = ""
    ticket.login_url = ""
    if ticket.account_id != ZERO_UUID:
        account = db.get(DoubaoAccount, ticket.account_id)
        if account is not None and account.status == STATUS_LOGGING_IN:
            account.status = STATUS_NEED_RELOGIN
    db.flush()
    return ticket


def complete_ticket_with_storage_state(
    db: Session,
    ticket_id: UUID,
    *,
    storage_state: dict[str, Any],
) -> tuple[DoubaoLoginTicket, DoubaoAccount]:
    ticket = get_ticket(db, ticket_id)
    return _complete_pending_ticket(db, ticket, storage_state=storage_state)


def complete_ticket_by_token(
    db: Session,
    token: str,
    *,
    storage_state: dict[str, Any],
) -> tuple[DoubaoLoginTicket, DoubaoAccount]:
    """Complete a pending ticket by possession of its high-entropy token (ops container callback)."""
    ticket = get_ticket_by_token(db, token)
    return _complete_pending_ticket(db, ticket, storage_state=storage_state)


def _complete_pending_ticket(
    db: Session,
    ticket: DoubaoLoginTicket,
    *,
    storage_state: dict[str, Any],
) -> tuple[DoubaoLoginTicket, DoubaoAccount]:
    if ticket.status == TICKET_EXPIRED:
        raise HTTPException(status_code=410, detail="Ticket expired")
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")
    require_session_storage_state(storage_state)

    account = upsert_account_from_state(
        db,
        label=ticket.label,
        storage_state=storage_state,
        status=STATUS_ACTIVE,
    )
    if (ticket.container_id or "").strip():
        stop_ops_session(ticket.container_id)
    ticket.account_id = account.id
    ticket.status = TICKET_SUCCEEDED
    ticket.completed_at = utc_now()
    ticket.error_text = ""
    ticket.login_url = ""
    ticket.container_id = ""
    db.flush()
    return ticket, account
