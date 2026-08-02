"""Redis bind tickets for WeChat MP webpage OAuth binding."""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import User
from aperix_geo.services.wechat.oauth import build_oauth_authorize_url
from aperix_geo.services.wechat.token import WechatError
from aperix_geo.utils.cache.redis_kv import require_redis_client

logger = logging.getLogger(__name__)

BindTicketStatus = Literal["pending", "bound", "failed", "expired"]

_KEY_PREFIX = "aperix:wechat_bind:v1:"


@dataclass
class BindTicket:
    ticket_id: str
    user_id: str
    status: BindTicketStatus
    # OAuth authorize URL (frontend encodes as QR for desktop scan).
    authorize_url: str = ""
    open_id: str = ""
    error: str = ""
    expires_in: int = 0

    @property
    def qrcode_url(self) -> str:
        """Backward-compatible alias for authorize_url."""
        return self.authorize_url


def _key(ticket_id: str) -> str:
    return f"{_KEY_PREFIX}{ticket_id}"


def _dump(ticket: BindTicket) -> str:
    return json.dumps(
        {
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "status": ticket.status,
            "authorize_url": ticket.authorize_url,
            # legacy field name kept for in-flight Redis tickets
            "qrcode_url": ticket.authorize_url,
            "open_id": ticket.open_id,
            "error": ticket.error,
            "expires_in": ticket.expires_in,
        },
        ensure_ascii=False,
    )


def _load(raw: str | bytes | None) -> BindTicket | None:
    if not raw:
        return None
    text = raw.decode() if isinstance(raw, bytes) else raw
    data = json.loads(text)
    authorize = str(data.get("authorize_url") or data.get("qrcode_url") or "")
    return BindTicket(
        ticket_id=str(data.get("ticket_id") or ""),
        user_id=str(data.get("user_id") or ""),
        status=data.get("status") or "pending",  # type: ignore[arg-type]
        authorize_url=authorize,
        open_id=str(data.get("open_id") or ""),
        error=str(data.get("error") or ""),
        expires_in=int(data.get("expires_in") or 0),
    )


def create_bind_ticket(*, user_id: uuid.UUID, settings: Settings | None = None) -> BindTicket:
    s = settings or get_settings()
    ttl = int(s.wechat_bind_ttl_seconds)
    ticket_id = secrets.token_urlsafe(18)[:32]
    authorize_url = build_oauth_authorize_url(state=ticket_id, settings=s)
    ticket = BindTicket(
        ticket_id=ticket_id,
        user_id=str(user_id),
        status="pending",
        authorize_url=authorize_url,
        expires_in=ttl,
    )
    r = require_redis_client()
    r.setex(_key(ticket_id), ttl, _dump(ticket))
    return ticket


def get_bind_ticket(ticket_id: str) -> BindTicket | None:
    r = require_redis_client()
    tid = ticket_id.strip()
    if not tid:
        return None
    ticket = _load(r.get(_key(tid)))
    if ticket is None:
        return BindTicket(ticket_id=tid, user_id="", status="expired")
    return ticket


def _save(ticket: BindTicket, *, ttl_seconds: int | None = None) -> None:
    r = require_redis_client()
    key = _key(ticket.ticket_id)
    if ttl_seconds is None:
        ttl = r.ttl(key)
        ttl_seconds = ttl if isinstance(ttl, int) and ttl > 0 else 60
    r.setex(key, max(30, int(ttl_seconds)), _dump(ticket))


def complete_bind(
    db: Session,
    *,
    ticket_id: str,
    open_id: str,
    nick_name: str = "",
    union_id: str = "",
) -> BindTicket | None:
    """Bind open_id (+ optional nick/union) to the ticket owner. Idempotent."""
    ticket = get_bind_ticket(ticket_id)
    if ticket is None or ticket.status == "expired" or not ticket.user_id:
        logger.info("WeChat bind ticket missing/expired ticket=%s", ticket_id[:12])
        return ticket
    if ticket.status == "bound":
        return ticket
    if ticket.status == "failed":
        return ticket

    oid = open_id.strip()
    if not oid:
        ticket.status = "failed"
        ticket.error = "缺少微信 open_id"
        _save(ticket)
        return ticket

    try:
        user_uuid = uuid.UUID(ticket.user_id)
    except ValueError:
        ticket.status = "failed"
        ticket.error = "绑定票据无效"
        _save(ticket)
        return ticket

    existing = db.execute(select(User).where(User.open_id == oid)).scalar_one_or_none()
    if existing is not None and existing.id != user_uuid:
        ticket.status = "failed"
        ticket.error = "该微信已绑定其他账号"
        ticket.open_id = oid
        _save(ticket)
        return ticket

    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        ticket.status = "failed"
        ticket.error = "用户不存在或已停用"
        _save(ticket)
        return ticket

    nick = nick_name.strip()
    uid = union_id.strip()

    user.open_id = oid
    if uid:
        user.union_id = uid
    if nick:
        user.nick_name = nick
    elif not user.nick_name.strip():
        user.nick_name = "微信用户"
    db.commit()

    ticket.status = "bound"
    ticket.open_id = oid
    ticket.error = ""
    _save(ticket)
    logger.info("WeChat bind success user=%s openid=%s nick=%s", user.id, oid[:8], bool(nick))
    return ticket


def complete_bind_from_scan(
    db: Session,
    *,
    ticket_id: str,
    open_id: str,
    settings: Settings | None = None,
) -> BindTicket | None:
    """Legacy MP SCAN/subscribe path (no nickname). Prefer OAuth callback."""
    _ = settings
    try:
        return complete_bind(db, ticket_id=ticket_id, open_id=open_id)
    except WechatError:
        raise
