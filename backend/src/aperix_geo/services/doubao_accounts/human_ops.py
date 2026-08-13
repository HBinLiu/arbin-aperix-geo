"""Human ops recovery for Doubao crawl accounts (ticket + alert).

Login expiry and behavior captcha share this path — never auto-solve captcha,
and never treat captcha as a special in-browser wait. Sampling falls back to API;
ops clears the account via login ticket (noVNC / storage_state upload).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import DoubaoAccount, DoubaoLoginTicket
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.alerts.state import evaluate_alert_gate, mark_alert_sent
from aperix_geo.services.doubao_accounts.pool import mark_need_relogin
from aperix_geo.services.doubao_accounts.tickets import (
    TICKET_PENDING,
    create_login_ticket,
    novnc_configured,
)

logger = logging.getLogger(__name__)

HumanReason = Literal["login_expired", "captcha"]

_REASON_LABEL = {
    "login_expired": "登录失效",
    "captcha": "行为验证码",
}


def request_human_intervention(
    db: Session,
    *,
    account_id: uuid.UUID,
    reason: HumanReason,
    error: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Mark need_relogin, ensure a pending ticket, and alert ops (same for captcha/login)."""
    settings = settings or get_settings()
    message = (error or reason).strip()
    mark_need_relogin(db, account_id=account_id, error=message)

    account = db.get(DoubaoAccount, account_id)
    label = account.label if account is not None else ""
    ticket = _ensure_pending_ticket(
        db,
        account_id=account_id,
        label=label,
        reason=reason,
        error=message,
        settings=settings,
    )
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
    }


def _ensure_pending_ticket(
    db: Session,
    *,
    account_id: uuid.UUID,
    label: str,
    reason: HumanReason,
    error: str,
    settings: Settings,
) -> DoubaoLoginTicket | None:
    if not settings.doubao_ops_ticket_enabled:
        return None

    existing = db.scalars(
        select(DoubaoLoginTicket)
        .where(
            DoubaoLoginTicket.account_id == account_id,
            DoubaoLoginTicket.status == TICKET_PENDING,
        )
        .limit(1)
    ).first()
    if existing is not None:
        return existing

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
        return None

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
    return ticket


def _maybe_alert_ops(
    *,
    account_id: uuid.UUID,
    label: str,
    reason: HumanReason,
    error: str,
    ticket: DoubaoLoginTicket | None,
    settings: Settings,
) -> bool:
    if not settings.provider_alert_enabled:
        return False
    email_to = [
        part.strip()
        for part in (settings.provider_alert_email_to or "").split(",")
        if part.strip()
    ]
    if not email_to:
        return False

    gate_id = f"doubao_account:{account_id}"
    gate = evaluate_alert_gate(
        gate_id,
        min_fails=1,
        cooldown_seconds=settings.provider_alert_cooldown_seconds,
    )
    if not gate.should_notify:
        return False

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
            f"账号 label：{label or '—'}",
            f"账号 ID：{account_id}",
            f"原因：{reason_cn}（{reason}）",
            "",
            "错误摘要：",
            (error or "—")[:1500],
            "",
            ticket_line,
            "",
            "处理：打开/完成豆包登录工单（noVNC 或上传 storage_state），恢复后账号回 active。",
            "采样侧本条可走 API 兜底；验证码禁止自动打码。",
            f"noVNC 配置：{'是' if novnc_configured(settings) else '否（upload fallback）'}",
        ]
    )
    try:
        send_alert_email(settings, to_addrs=email_to, subject=subject, body=body)
    except Exception:
        logger.warning("doubao human-ops alert email failed account=%s", account_id, exc_info=True)
        return False
    mark_alert_sent(gate_id)
    return True
