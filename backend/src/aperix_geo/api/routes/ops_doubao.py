"""Ops Doubao account / login-ticket APIs.

Auth: ``Authorization: Bearer <DOUBAO_OPS_API_TOKEN>`` or header ``X-Doubao-Ops-Token``.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aperix_geo.api.deps import DbSession
from aperix_geo.config import get_settings
from aperix_geo.services.doubao_accounts import tickets as ticket_svc
from aperix_geo.services.doubao_accounts.pool import upsert_account_from_state

router = APIRouter(prefix="/ops/doubao", tags=["ops-doubao"])
_ops_bearer = HTTPBearer(auto_error=False)


def require_doubao_ops(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_ops_bearer)],
    x_doubao_ops_token: Annotated[str | None, Header(alias="X-Doubao-Ops-Token")] = None,
) -> None:
    expected = (get_settings().doubao_ops_api_token or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doubao ops API not configured (set DOUBAO_OPS_API_TOKEN)",
        )
    provided = ""
    if credentials and credentials.credentials:
        provided = credentials.credentials.strip()
    elif x_doubao_ops_token:
        provided = x_doubao_ops_token.strip()
    if not provided or provided != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid ops token")


OpsAuth = Annotated[None, Depends(require_doubao_ops)]


class UpsertAccountBody(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    storage_state: dict[str, Any]


class CreateTicketBody(BaseModel):
    label: str = ""
    account_id: UUID | None = None
    operator: str = ""
    reason: str = Field(default="login_expired", pattern="^(login_expired|captcha)$")


class CompleteTicketBody(BaseModel):
    storage_state: dict[str, Any]


class CompleteByTokenBody(BaseModel):
    token: str = Field(min_length=8, max_length=64)
    storage_state: dict[str, Any]


@router.get("/accounts")
def ops_list_accounts(_: OpsAuth, db: DbSession) -> dict[str, Any]:
    rows = ticket_svc.list_accounts(db)
    return {"items": [ticket_svc.account_to_dict(r) for r in rows]}


@router.post("/accounts")
def ops_upsert_account(_: OpsAuth, db: DbSession, body: UpsertAccountBody) -> dict[str, Any]:
    row = upsert_account_from_state(db, label=body.label, storage_state=body.storage_state)
    db.commit()
    db.refresh(row)
    return ticket_svc.account_to_dict(row)


@router.post("/tickets")
def ops_create_ticket(_: OpsAuth, db: DbSession, body: CreateTicketBody) -> dict[str, Any]:
    ticket = ticket_svc.create_login_ticket(
        db,
        label=body.label,
        account_id=body.account_id,
        operator=body.operator,
        reason=body.reason,
    )
    db.commit()
    db.refresh(ticket)
    return ticket_svc.ticket_to_dict(ticket)


@router.get("/tickets/{ticket_id}")
def ops_get_ticket(_: OpsAuth, db: DbSession, ticket_id: UUID) -> dict[str, Any]:
    ticket = ticket_svc.get_ticket(db, ticket_id)
    db.commit()
    return ticket_svc.ticket_to_dict(ticket)


@router.post("/tickets/{ticket_id}/complete")
def ops_complete_ticket(
    _: OpsAuth,
    db: DbSession,
    ticket_id: UUID,
    body: CompleteTicketBody,
) -> dict[str, Any]:
    ticket, account = ticket_svc.complete_ticket_with_storage_state(
        db,
        ticket_id,
        storage_state=body.storage_state,
    )
    db.commit()
    return {
        "ticket": ticket_svc.ticket_to_dict(ticket),
        "account": ticket_svc.account_to_dict(account),
    }


@router.post("/tickets/complete-by-token")
def ops_complete_ticket_by_token(db: DbSession, body: CompleteByTokenBody) -> dict[str, Any]:
    """Public to geo-crawl-ops containers: auth is possession of the pending ticket token."""
    ticket, account = ticket_svc.complete_ticket_by_token(
        db,
        body.token,
        storage_state=body.storage_state,
    )
    db.commit()
    return {
        "ticket": ticket_svc.ticket_to_dict(ticket),
        "account": ticket_svc.account_to_dict(account),
    }


@router.post("/tickets/{ticket_id}/cancel")
def ops_cancel_ticket(_: OpsAuth, db: DbSession, ticket_id: UUID) -> dict[str, Any]:
    ticket = ticket_svc.cancel_ticket(db, ticket_id)
    db.commit()
    return ticket_svc.ticket_to_dict(ticket)
