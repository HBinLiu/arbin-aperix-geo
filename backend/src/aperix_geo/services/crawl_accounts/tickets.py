"""Geo crawl account tickets: create / complete / cancel (geo-web-crawl noVNC or upload)."""

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
from aperix_geo.db.models import EPOCH, ZERO_UUID, CrawlAccount, CrawlLoginTicket
from aperix_geo.services.crawl_accounts.cookies import (
    storage_state_has_session_cookies,
)
from aperix_geo.services.crawl_accounts.platforms import (
    PLATFORM_DOUBAO,
    normalize_login_reason,
    normalize_platform,
    platform_start_url,
)
from aperix_geo.services.crawl_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_LOGGING_IN,
    STATUS_NEED_RELOGIN,
    activate_account_after_login,
    apply_ops_handoff_lease,
    ensure_account_for_ops,
    upsert_account_from_state,
)
from aperix_geo.services.crawl_accounts.ticket_urls import (
    advertised_vnc_port,
    build_complete_callback_url,
    build_login_url,
    rewrite_loopback_callback_url,
)
from aperix_geo.services.crawl_browser.client import (
    CrawlLoginClientError,
    crawl_login_session_running,
    start_crawl_login_session,
    stop_crawl_login_session,
)

logger = logging.getLogger(__name__)

TICKET_PENDING = "pending"
TICKET_SUCCEEDED = "succeeded"
TICKET_EXPIRED = "expired"
TICKET_CANCELLED = "cancelled"


def novnc_configured(settings: Settings | None = None) -> bool:
    """True when tickets can open headed Chrome via geo-web-crawl noVNC."""
    settings = settings or get_settings()
    return bool(
        settings.doubao_ops_ticket_enabled
        and (settings.geo_web_crawl_base_url or "").strip()
        and (settings.geo_crawl_ops_novnc_base_url or "").strip()
    )


def _ticket_account_id(ticket: CrawlLoginTicket) -> str:
    if ticket.account_id == ZERO_UUID:
        return ""
    return str(ticket.account_id)


def _ticket_session_id(ticket: CrawlLoginTicket) -> str:
    """Login session id stored in the historical ``container_id`` column."""
    return (ticket.container_id or "").strip()


def _clear_ticket_session(ticket: CrawlLoginTicket) -> None:
    ticket.container_id = ""
    ticket.login_url = ""


def _release_logging_in_account(db: Session, ticket: CrawlLoginTicket, *, error: str) -> None:
    """Pending ticket is gone: account must leave logging_in so heartbeat can reopen."""
    if ticket.account_id == ZERO_UUID:
        return
    account = db.get(CrawlAccount, ticket.account_id)
    if account is None:
        return
    if account.status == STATUS_LOGGING_IN:
        account.status = STATUS_NEED_RELOGIN
        account.last_error = (error or account.last_error or "login ticket closed").strip()[:2000]


def _expire_if_needed(db: Session, ticket: CrawlLoginTicket) -> bool:
    if ticket.status != TICKET_PENDING:
        return False
    if ticket.expires_at <= utc_now():
        ticket.status = TICKET_EXPIRED
        ticket.error_text = "ticket expired"
        if _ticket_session_id(ticket):
            _stop_ticket_desktop(ticket)
            _clear_ticket_session(ticket)
        _release_logging_in_account(db, ticket, error="login ticket expired")
        return True
    return False


def list_pending_tickets(
    db: Session,
    *,
    platform: str | None = None,
    limit: int = 50,
) -> list[CrawlLoginTicket]:
    stmt = (
        select(CrawlLoginTicket)
        .where(CrawlLoginTicket.status == TICKET_PENDING)
        .order_by(CrawlLoginTicket.created_at.asc())
        .limit(max(1, int(limit)))
    )
    if platform is not None and str(platform).strip():
        stmt = stmt.where(CrawlLoginTicket.platform == normalize_platform(platform))
    return list(db.scalars(stmt).all())


def ticket_to_dict(ticket: CrawlLoginTicket) -> dict[str, Any]:
    return {
        "id": str(ticket.id),
        "platform": ticket.platform,
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
    platform: str = PLATFORM_DOUBAO,
    label: str = "",
    account_id: UUID | None = None,
    operator: str = "",
    reason: str = "login_expired",
    settings: Settings | None = None,
) -> CrawlLoginTicket:
    settings = settings or get_settings()
    if not settings.doubao_ops_ticket_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geo crawl ops tickets disabled (DOUBAO_OPS_TICKET_ENABLED=false)",
        )

    plat = normalize_platform(platform)
    reason = normalize_login_reason(reason)

    account: CrawlAccount | None = None
    resolved_label = (label or "").strip()
    resolved_account_id = ZERO_UUID
    storage_state: dict[str, Any] | None = None

    if account_id is not None and account_id != ZERO_UUID:
        account = db.get(CrawlAccount, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        plat = normalize_platform(account.platform)
        resolved_account_id = account.id
        resolved_label = account.label or resolved_label
        storage_state = dict(account.storage_state or {})
        account.lease_owner = ""
        account.lease_until = EPOCH

    if not resolved_label:
        resolved_label = f"{plat}-{uuid4().hex[:8]}"
    if account is None:
        account = ensure_account_for_ops(db, platform=plat, label=resolved_label)
        resolved_account_id = account.id
        resolved_label = account.label or resolved_label
        storage_state = dict(account.storage_state or {})
    account.status = STATUS_LOGGING_IN

    if resolved_account_id != ZERO_UUID:
        open_ticket = db.scalars(
            select(CrawlLoginTicket)
            .where(
                CrawlLoginTicket.account_id == resolved_account_id,
                CrawlLoginTicket.status == TICKET_PENDING,
            )
            .limit(1)
        ).first()
        if open_ticket is not None:
            raise HTTPException(status_code=409, detail="Account already has a pending login ticket")

    ttl_min = int(settings.doubao_ops_ticket_ttl_min)
    ticket = CrawlLoginTicket(
        id=uuid4(),
        platform=plat,
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
        _start_login_onto_ticket(
            ticket,
            storage_state=storage_state,
            reason=reason,
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
    ticket: CrawlLoginTicket,
    *,
    reason: str = "login_expired",
    settings: Settings | None = None,
) -> bool:
    settings = settings or get_settings()
    if _expire_if_needed(db, ticket):
        db.flush()
        return False
    if ticket.status != TICKET_PENDING:
        return False
    if not novnc_configured(settings):
        return False

    account_id = _ticket_account_id(ticket)
    if crawl_login_session_running(
        account_id,
        base_url=settings.geo_web_crawl_base_url,
        token=settings.geo_web_crawl_token,
    ):
        return False

    reason = normalize_login_reason(reason)

    storage_state: dict[str, Any] | None = None
    if ticket.account_id != ZERO_UUID:
        account = db.get(CrawlAccount, ticket.account_id)
        if account is not None:
            storage_state = dict(account.storage_state or {})
            if account.status != STATUS_LOGGING_IN:
                account.status = STATUS_LOGGING_IN

    if _ticket_session_id(ticket):
        _stop_ticket_desktop(ticket, settings=settings)

    ttl_min = int(settings.doubao_ops_ticket_ttl_min)
    ticket.expires_at = utc_now() + timedelta(minutes=ttl_min)
    started = _start_login_onto_ticket(
        ticket,
        storage_state=storage_state,
        reason=reason,
        ttl_min=ttl_min,
        settings=settings,
    )
    db.flush()
    if not started:
        return False
    logger.warning(
        "geo-web-crawl login respawned for pending ticket=%s session=%s url=%s",
        ticket.id,
        _ticket_session_id(ticket)[:32],
        (ticket.login_url or "")[:80],
    )
    return True


def _stop_ticket_desktop(
    ticket: CrawlLoginTicket,
    *,
    settings: Settings | None = None,
) -> None:
    """Close the headed login Chrome (VNC desktop stays)."""
    settings = settings or get_settings()
    account_id = _ticket_account_id(ticket)
    if not account_id:
        return
    stop_crawl_login_session(
        account_id,
        base_url=settings.geo_web_crawl_base_url,
        token=settings.geo_web_crawl_token,
    )


def _start_login_onto_ticket(
    ticket: CrawlLoginTicket,
    *,
    storage_state: dict[str, Any] | None,
    reason: str,
    ttl_min: int,
    settings: Settings,
) -> bool:
    plat = normalize_platform(ticket.platform)
    start_url = platform_start_url(plat, settings=settings)
    complete_url = rewrite_loopback_callback_url(
        build_complete_callback_url(settings.geo_crawl_ops_callback_base_url)
    )
    try:
        data = start_crawl_login_session(
            account_id=str(ticket.account_id),
            platform=plat,
            start_url=start_url,
            ticket_token=ticket.token,
            complete_url=complete_url,
            ttl_min=ttl_min,
            reason=reason,
            baseline_storage_state=storage_state,
            base_url=settings.geo_web_crawl_base_url,
            token=settings.geo_web_crawl_token,
        )
        session_id = str(data.get("session_id") or "").strip() or (
            f"crawl-login:{ticket.account_id}"
        )
        ticket.container_id = session_id
        ticket.login_url = build_login_url(
            settings.geo_crawl_ops_novnc_base_url,
            ticket_token=ticket.token,
            host_port=advertised_vnc_port(data.get("vnc_port")),
        )
        ticket.error_text = (
            f"crawl_login: platform={plat} reason={reason} session={session_id}"
        )
        return bool((ticket.login_url or "").strip())
    except CrawlLoginClientError as exc:
        logger.warning(
            "geo-web-crawl login start failed; retry later ticket=%s: %s",
            ticket.id,
            exc,
        )
        _clear_ticket_session(ticket)
        ticket.error_text = f"novnc_start_failed: {exc}"
        return False


def get_ticket(db: Session, ticket_id: UUID) -> CrawlLoginTicket:
    ticket = db.get(CrawlLoginTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if _expire_if_needed(db, ticket):
        db.flush()
    return ticket


def get_ticket_by_token(db: Session, token: str) -> CrawlLoginTicket:
    tok = (token or "").strip()
    if not tok:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = db.scalars(
        select(CrawlLoginTicket).where(CrawlLoginTicket.token == tok).limit(1)
    ).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if _expire_if_needed(db, ticket):
        db.flush()
    return ticket


def require_session_storage_state(
    storage_state: dict[str, Any],
    *,
    platform: str = PLATFORM_DOUBAO,
) -> None:
    plat = normalize_platform(platform)
    if not storage_state_has_session_cookies(storage_state, platform=plat):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"storage_state missing {plat} session cookies",
        )


def _login_complete_allowed(
    storage_state: dict[str, Any],
    *,
    ticket: CrawlLoginTicket,
    platform: str,
    settings: Settings | None = None,
) -> None:
    """Accept session cookies or a ready Chrome profile (production noVNC path)."""
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    root = (settings.geo_crawl_profile_root or "").strip()
    if root and ticket.account_id != ZERO_UUID:
        from aperix_geo.services.crawl_accounts.profiles import (
            account_profile_dir,
            profile_is_ready,
        )

        profile_dir = account_profile_dir(plat, ticket.account_id, root=root)
        if profile_is_ready(profile_dir):
            return
    require_session_storage_state(storage_state, platform=plat)


def _account_from_completed_ticket(
    db: Session,
    ticket: CrawlLoginTicket,
    *,
    storage_state: dict[str, Any],
    platform: str,
) -> CrawlAccount:
    plat = normalize_platform(platform)
    if ticket.account_id != ZERO_UUID:
        account = db.get(CrawlAccount, ticket.account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return activate_account_after_login(
            db,
            account,
            storage_state=storage_state,
            platform=plat,
        )
    return upsert_account_from_state(
        db,
        label=ticket.label,
        storage_state=storage_state,
        platform=plat,
        status=STATUS_ACTIVE,
    )


def _schedule_post_login_heartbeat(
    account_id: UUID,
    *,
    settings: Settings | None = None,
) -> None:
    """After noVNC handoff, prove the profile with a real probe (short send)."""
    settings = settings or get_settings()
    if not settings.doubao_heartbeat_enabled:
        return
    handoff_s = max(0, int(settings.doubao_ops_handoff_s or 0))
    countdown = max(30, handoff_s + 15)
    try:
        from aperix_geo.tasks.crawl_accounts import crawl_account_heartbeat_account

        crawl_account_heartbeat_account.apply_async(
            args=[str(account_id)],
            kwargs={"platform": PLATFORM_DOUBAO},
            countdown=countdown,
        )
        logger.info(
            "post-login heartbeat scheduled account=%s countdown_s=%s",
            account_id,
            countdown,
        )
    except Exception:
        logger.warning(
            "post-login heartbeat enqueue failed account=%s",
            account_id,
            exc_info=True,
        )


def cancel_ticket(db: Session, ticket_id: UUID) -> CrawlLoginTicket:
    ticket = get_ticket(db, ticket_id)
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")
    if _ticket_session_id(ticket):
        _stop_ticket_desktop(ticket)
    ticket.status = TICKET_CANCELLED
    ticket.error_text = "cancelled"
    _clear_ticket_session(ticket)
    _release_logging_in_account(db, ticket, error="login ticket cancelled")
    db.flush()
    return ticket


def complete_ticket_with_storage_state(
    db: Session,
    ticket_id: UUID,
    *,
    storage_state: dict[str, Any],
) -> tuple[CrawlLoginTicket, CrawlAccount]:
    ticket = get_ticket(db, ticket_id)
    return _complete_pending_ticket(db, ticket, storage_state=storage_state)


def complete_ticket_by_token(
    db: Session,
    token: str,
    *,
    storage_state: dict[str, Any],
) -> tuple[CrawlLoginTicket, CrawlAccount]:
    ticket = get_ticket_by_token(db, token)
    return _complete_pending_ticket(db, ticket, storage_state=storage_state)


def _complete_pending_ticket(
    db: Session,
    ticket: CrawlLoginTicket,
    *,
    storage_state: dict[str, Any],
) -> tuple[CrawlLoginTicket, CrawlAccount]:
    if ticket.status == TICKET_EXPIRED:
        raise HTTPException(status_code=410, detail="Ticket expired")
    if ticket.status != TICKET_PENDING:
        raise HTTPException(status_code=409, detail=f"Ticket not pending ({ticket.status})")
    plat = normalize_platform(ticket.platform)
    _login_complete_allowed(storage_state, ticket=ticket, platform=plat, settings=get_settings())

    # Login Chrome is in geo-web-crawl. The watcher POSTs this endpoint then
    # closes Chromium itself — do not join/stop that thread here (deadlock).
    had_session = bool(_ticket_session_id(ticket))
    account = _account_from_completed_ticket(
        db,
        ticket,
        storage_state=storage_state,
        platform=plat,
    )
    if had_session:
        apply_ops_handoff_lease(account)
    ticket.account_id = account.id
    ticket.status = TICKET_SUCCEEDED
    ticket.completed_at = utc_now()
    ticket.error_text = ""
    _clear_ticket_session(ticket)
    db.flush()
    _schedule_post_login_heartbeat(account.id)
    return ticket, account
