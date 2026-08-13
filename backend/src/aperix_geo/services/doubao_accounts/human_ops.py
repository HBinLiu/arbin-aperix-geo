"""Human ops recovery for Doubao crawl accounts (ticket + alert).

Login expiry and behavior captcha share this path — never auto-solve captcha,
and never treat captcha as a special in-browser wait. Sampling falls back to API;
ops clears the account via login ticket (noVNC / storage_state upload).

通知策略：有工单 / 人工介入时发信（无冷却、失败重试）；心跳正常探活不发摘要。
不沿用 PROVIDER_ALERT_COOLDOWN（该冷却仅影响欠费等平台告警）。
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import DoubaoAccount, DoubaoLoginTicket
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.doubao_accounts.pool import mark_need_relogin
from aperix_geo.services.doubao_accounts.tickets import (
    TICKET_PENDING,
    create_login_ticket,
    ensure_pending_ticket_session,
)

logger = logging.getLogger(__name__)

HumanReason = Literal["login_expired", "captcha"]

_REASON_LABEL = {
    "login_expired": "登录失效",
    "captcha": "行为验证码",
}

_EMAIL_ATTEMPTS = 3
_EMAIL_RETRY_SLEEP_S = 1.5


def _alert_recipients(settings: Settings) -> list[str]:
    return [
        part.strip()
        for part in (settings.provider_alert_email_to or "").split(",")
        if part.strip()
    ]


def send_ops_alert_email(
    settings: Settings,
    *,
    subject: str,
    body: str,
    context: str = "ops",
) -> bool:
    """Send ops email with retries. Returns True when delivered."""
    if not settings.provider_alert_enabled:
        logger.info("ops alert skipped (%s): PROVIDER_ALERT_ENABLED=false", context)
        return False
    email_to = _alert_recipients(settings)
    if not email_to:
        logger.warning("ops alert skipped (%s): PROVIDER_ALERT_EMAIL_TO empty", context)
        return False

    last_exc: Exception | None = None
    for attempt in range(1, _EMAIL_ATTEMPTS + 1):
        try:
            send_alert_email(settings, to_addrs=email_to, subject=subject, body=body)
            logger.info(
                "ops alert emailed context=%s to=%s attempt=%s subject=%s",
                context,
                email_to,
                attempt,
                subject[:120],
            )
            return True
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "ops alert email failed context=%s attempt=%s/%s: %s",
                context,
                attempt,
                _EMAIL_ATTEMPTS,
                exc,
                exc_info=attempt == _EMAIL_ATTEMPTS,
            )
            if attempt < _EMAIL_ATTEMPTS:
                time.sleep(_EMAIL_RETRY_SLEEP_S)
    logger.error("ops alert email exhausted retries context=%s err=%s", context, last_exc)
    return False


def request_human_intervention(
    db: Session,
    *,
    account_id: uuid.UUID,
    reason: HumanReason,
    error: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Mark need_relogin, ensure a pending ticket (+ live noVNC), and alert when actionable."""
    settings = settings or get_settings()
    message = (error or reason).strip()
    mark_need_relogin(db, account_id=account_id, error=message)

    account = db.get(DoubaoAccount, account_id)
    label = account.label if account is not None else ""
    ticket, alert_needed = _ensure_pending_ticket(
        db,
        account_id=account_id,
        label=label,
        reason=reason,
        error=message,
        settings=settings,
    )
    alerted = False
    if alert_needed:
        alerted = _maybe_alert_ops(
            account_id=account_id,
            label=label,
            reason=reason,
            error=message,
            ticket=ticket,
            settings=settings,
        )
    return {
        "account_id": str(account_id),
        "reason": reason,
        "ticket_id": str(ticket.id) if ticket is not None else "",
        "alerted": alerted,
        "session_refreshed": alert_needed and ticket is not None,
    }


def _ensure_pending_ticket(
    db: Session,
    *,
    account_id: uuid.UUID,
    label: str,
    reason: HumanReason,
    error: str,
    settings: Settings,
) -> tuple[DoubaoLoginTicket | None, bool]:
    """Return (ticket, should_alert). Alert on new ticket or respawned dead session."""
    if not settings.doubao_ops_ticket_enabled:
        return None, True  # still alert that human ops is needed (no ticket)

    existing = db.scalars(
        select(DoubaoLoginTicket)
        .where(
            DoubaoLoginTicket.account_id == account_id,
            DoubaoLoginTicket.status == TICKET_PENDING,
        )
        .limit(1)
    ).first()
    if existing is not None:
        respawned = ensure_pending_ticket_session(
            db, existing, reason=reason, settings=settings
        )
        if existing.status != TICKET_PENDING:
            # Expired while ensuring — fall through to create a fresh ticket.
            existing = None
        else:
            return existing, respawned

    try:
        ticket = create_login_ticket(
            db,
            account_id=account_id,
            label=label,
            operator="system",
            reason=reason,
            settings=settings,
        )
    except Exception:
        logger.warning(
            "doubao human-ops ticket create failed account=%s reason=%s",
            account_id,
            reason,
            exc_info=True,
        )
        return None, True

    prefix = f"auto:{reason}"
    detail = (error or "").strip()
    # Preserve create_login_ticket hint (novnc_unavailable / spawn_pending) after reason.
    prev = (ticket.error_text or "").strip()
    ticket.error_text = f"{prefix}: {detail}"[:1800] + (f" | {prev}" if prev else "")
    db.flush()
    logger.warning(
        "doubao human-ops ticket opened id=%s account=%s reason=%s",
        ticket.id,
        account_id,
        reason,
    )
    return ticket, True


def _maybe_alert_ops(
    *,
    account_id: uuid.UUID,
    label: str,
    reason: HumanReason,
    error: str,
    ticket: DoubaoLoginTicket | None,
    settings: Settings,
) -> bool:
    """Always attempt email on ticket / human-ops (no cooldown)."""
    reason_cn = _REASON_LABEL.get(reason, reason)
    env = (getattr(settings, "env", None) or "unknown").strip() or "unknown"
    subject = f"[Aperix GEO] 豆包账号需人工处理：{reason_cn} ({env})"
    ticket_line = (
        f"工单 ID：{ticket.id}\n登录 URL：{ticket.login_url or '（upload_fallback，请回传 storage_state）'}"
        if ticket is not None
        else "工单：未创建（DOUBAO_OPS_TICKET_ENABLED=false 或创建失败）"
    )
    body = "\n".join(
        [
            f"环境：{env}",
            "账号平台：豆包",
            f"账号 ID：{account_id}",
            f"账号 label：{label or '—'}",
            f"原因：{reason_cn}（{reason}）",
            "",
            "错误摘要：",
            (error or "—")[:1500],
            "",
            ticket_line,
            "",
            "处理：打开/完成豆包登录工单（noVNC 或上传 storage_state），恢复后账号回 active。",
        ]
    )
    return send_ops_alert_email(
        settings,
        subject=subject,
        body=body,
        context=f"doubao_ticket:{account_id}",
    )
