"""Doubao login tickets: create / complete / cancel (upload fallback; noVNC optional)."""

from __future__ import annotations

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

TICKET_PENDING = "pending"
TICKET_SUCCEEDED = "succeeded"
TICKET_FAILED = "failed"
TICKET_EXPIRED = "expired"
TICKET_CANCELLED = "cancelled"


def novnc_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(
        settings.doubao_login_ticket_enabled
        and (settings.doubao_login_novnc_base_url or "").strip()
        and (settings.doubao_login_docker_image or "").strip()
    )


def _expire_if_needed(ticket: DoubaoLoginTicket) -> bool:
    if ticket.status != TICKET_PENDING:
        return False
    if ticket.expires_at <= utc_now():
        ticket.status = TICKET_EXPIRED
        ticket.error_text = "ticket expired"
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
        "upload_fallback": not novnc_configured(settings) or not ticket.login_url.strip(),
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
    settings: Settings | None = None,
) -> DoubaoLoginTicket:
    settings = settings or get_settings()
    if not settings.doubao_login_ticket_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doubao login tickets disabled (DOUBAO_LOGIN_TICKET_ENABLED=false)",
        )

    account: DoubaoAccount | None = None
    resolved_label = (label or "").strip()
    resolved_account_id = ZERO_UUID

    if account_id is not None and account_id != ZERO_UUID:
        account = db.get(DoubaoAccount, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        resolved_account_id = account.id
        resolved_label = account.label or resolved_label
        account.status = STATUS_LOGGING_IN
        account.lease_owner = ""
        account.lease_until = EPOCH

    if not resolved_label:
        resolved_label = f"doubao-{uuid4().hex[:8]}"

    # Single open ticket per account when updating existing.
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

    ttl_min = int(settings.doubao_login_ticket_ttl_min)
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
        # Docker/noVNC spawn is ops infrastructure; P4 returns structured placeholder.
        # Real container orchestration lands with the login image deployment.
        base = settings.doubao_login_novnc_base_url.rstrip("/")
        ticket.login_url = f"{base}/?ticket={ticket.token}"
        ticket.error_text = "novnc_spawn_pending: configure worker to attach session"
    else:
        ticket.error_text = "novnc_unavailable: complete via storage_state upload"

    db.add(ticket)
    db.flush()
    return ticket


def get_ticket(db: Session, ticket_id: UUID) -> DoubaoLoginTicket:
    ticket = db.get(DoubaoLoginTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if _expire_if_needed(ticket):
        db.flush()
    return ticket


def cancel_ticket(db: Session, ticket_id: UUID) -> DoubaoLoginTicket:
    ticket = get_ticket(db, ticket_id)
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")
    ticket.status = TICKET_CANCELLED
    ticket.error_text = "cancelled"
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
    if ticket.status == TICKET_EXPIRED:
        raise HTTPException(status_code=410, detail="Ticket expired")
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")

    account = upsert_account_from_state(
        db,
        label=ticket.label,
        storage_state=storage_state,
        status=STATUS_ACTIVE,
    )
    ticket.account_id = account.id
    ticket.status = TICKET_SUCCEEDED
    ticket.completed_at = utc_now()
    ticket.error_text = ""
    ticket.login_url = ""
    ticket.container_id = ""
    db.flush()
    return ticket, account
