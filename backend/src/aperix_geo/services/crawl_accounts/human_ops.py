"""Human ops recovery for geo crawl accounts (ticket + alert)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import ZERO_UUID, CrawlAccount, CrawlLoginTicket
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform
from aperix_geo.services.crawl_accounts.pool import mark_need_relogin
from aperix_geo.services.crawl_accounts.tickets import (
    TICKET_EXPIRED,
    TICKET_PENDING,
    create_login_ticket,
    ensure_pending_ticket_session,
    list_pending_tickets,
    novnc_configured,
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
    settings = settings or get_settings()
    message = (error or reason).strip()
    mark_need_relogin(db, account_id=account_id, error=message)

    account = db.get(CrawlAccount, account_id)
    label = account.label if account is not None else ""
    platform = normalize_platform(
        account.platform if account is not None else PLATFORM_DOUBAO
    )
    ticket, alert_needed = _ensure_pending_ticket(
        db,
        account_id=account_id,
        label=label,
        platform=platform,
        reason=reason,
        error=message,
        settings=settings,
    )
    alerted = False
    if alert_needed:
        alerted = _maybe_alert_ops(
            account_id=account_id,
            label=label,
            platform=platform,
            reason=reason,
            error=message,
            ticket=ticket,
            settings=settings,
        )
    return {
        "account_id": str(account_id),
        "platform": platform,
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
    platform: str,
    reason: HumanReason,
    error: str,
    settings: Settings,
) -> tuple[CrawlLoginTicket | None, bool]:
    if not settings.doubao_ops_ticket_enabled:
        return None, True

    existing = db.scalars(
        select(CrawlLoginTicket)
        .where(
            CrawlLoginTicket.account_id == account_id,
            CrawlLoginTicket.status == TICKET_PENDING,
        )
        .limit(1)
    ).first()
    if existing is not None:
        respawned = ensure_pending_ticket_session(
            db, existing, reason=reason, settings=settings
        )
        if existing.status != TICKET_PENDING:
            existing = None
        else:
            return existing, respawned

    try:
        ticket = create_login_ticket(
            db,
            platform=platform,
            account_id=account_id,
            label=label,
            operator="system",
            reason=reason,
            settings=settings,
        )
    except Exception:
        logger.warning(
            "geo crawl human-ops ticket create failed account=%s platform=%s reason=%s",
            account_id,
            platform,
            reason,
            exc_info=True,
        )
        return None, _should_alert_ticket(None, settings)

    prefix = f"auto:{reason}"
    detail = (error or "").strip()
    prev = (ticket.error_text or "").strip()
    ticket.error_text = f"{prefix}: {detail}"[:1800] + (f" | {prev}" if prev else "")
    db.flush()
    logger.warning(
        "geo crawl human-ops ticket opened id=%s account=%s platform=%s reason=%s",
        ticket.id,
        account_id,
        platform,
        reason,
    )
    return ticket, _should_alert_ticket(ticket, settings)


def sweep_stale_login_tickets(
    db: Session,
    *,
    platform: str = PLATFORM_DOUBAO,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Unstick logging_in + pending when noVNC died or the ticket TTL elapsed.

    Heartbeat must skip live VNC sessions, so dead sessions would otherwise
    sit forever. Beat should call this even when the login probe is skipped.
    """
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    if not settings.doubao_ops_ticket_enabled:
        return {"expired": 0, "respawned": 0, "reopened": 0}

    expired = 0
    respawned = 0
    reopened = 0
    tickets = list_pending_tickets(db, platform=plat)
    for ticket in tickets:
        if ensure_pending_ticket_session(
            db, ticket, reason="login_expired", settings=settings
        ):
            respawned += 1
            if _should_alert_ticket(ticket, settings):
                account = db.get(CrawlAccount, ticket.account_id)
                _maybe_alert_ops(
                    account_id=ticket.account_id,
                    label=(account.label if account is not None else ticket.label)
                    or ticket.label,
                    platform=plat,
                    reason="login_expired",
                    error="noVNC session ended; restarted remote desktop",
                    ticket=ticket,
                    settings=settings,
                )
            continue
        if ticket.status != TICKET_EXPIRED:
            continue
        expired += 1
        if ticket.account_id == ZERO_UUID:
            continue
        request_human_intervention(
            db,
            account_id=ticket.account_id,
            reason="login_expired",
            error="login ticket expired; opened a new noVNC session",
            settings=settings,
        )
        reopened += 1

    db.flush()
    if expired or respawned or reopened:
        logger.warning(
            "geo crawl ticket sweep platform=%s expired=%s respawned=%s reopened=%s",
            plat,
            expired,
            respawned,
            reopened,
        )
    return {"expired": expired, "respawned": respawned, "reopened": reopened}


def _ticket_login_url(ticket: CrawlLoginTicket | None) -> str:
    if ticket is None:
        return ""
    return (ticket.login_url or "").strip()


def _should_alert_ticket(ticket: CrawlLoginTicket | None, settings: Settings) -> bool:
    """Skip the empty-URL mail when noVNC is configured; retry until the desktop is up."""
    if ticket is None:
        return not novnc_configured(settings)
    if _ticket_login_url(ticket):
        return True
    return not novnc_configured(settings)


def _maybe_alert_ops(
    *,
    account_id: uuid.UUID,
    label: str,
    platform: str,
    reason: HumanReason,
    error: str,
    ticket: CrawlLoginTicket | None,
    settings: Settings,
) -> bool:
    if not _should_alert_ticket(ticket, settings):
        logger.warning(
            "ops alert skipped (waiting for noVNC url) account=%s ticket=%s",
            account_id,
            None if ticket is None else ticket.id,
        )
        return False
    reason_cn = _REASON_LABEL.get(reason, reason)
    env = (getattr(settings, "env", None) or "unknown").strip() or "unknown"
    subject = f"[Aperix GEO] 爬虫账号需人工处理：{platform}/{reason_cn} ({env})"
    ticket_line = (
        f"工单 ID：{ticket.id}\n登录 URL：{ticket.login_url or '（upload_fallback，请回传 storage_state）'}"
        if ticket is not None
        else "工单：未创建（DOUBAO_OPS_TICKET_ENABLED=false 或创建失败）"
    )
    body = "\n".join(
        [
            f"环境：{env}",
            f"账号平台：{platform}",
            f"账号 ID：{account_id}",
            f"账号 label：{label or '—'}",
            f"原因：{reason_cn}（{reason}）",
            "",
            "错误摘要：",
            (error or "—")[:1500],
            "",
            ticket_line,
            "",
            "处理：打开/完成登录工单（noVNC 或上传 storage_state），恢复后账号回 active。",
        ]
    )
    return send_ops_alert_email(
        settings,
        subject=subject,
        body=body,
        context=f"geo_crawl_ticket:{platform}:{account_id}",
    )
