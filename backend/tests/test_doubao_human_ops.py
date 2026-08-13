"""Tests for Doubao human ops (ticket + alert) recovery path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.config import Settings
from aperix_geo.db.models import DoubaoAccount, DoubaoLoginTicket
from aperix_geo.services.doubao_accounts.human_ops import request_human_intervention
from aperix_geo.services.doubao_accounts.pool import STATUS_NEED_RELOGIN
from aperix_geo.services.doubao_accounts.tickets import TICKET_PENDING


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_ops_ticket_enabled": True,
        "doubao_ops_ticket_ttl_min": 15,
        "geo_crawl_ops_novnc_base_url": "",
        "geo_crawl_ops_docker_image": "",
        "provider_alert_enabled": True,
        "provider_alert_email_to": "ops@example.com",
        "provider_alert_cooldown_seconds": 60,
        "env": "test",
    }
    base.update(kwargs)
    return Settings(**base)


def test_request_human_intervention_opens_ticket_and_alerts() -> None:
    account_id = uuid4()
    account = DoubaoAccount(
        id=account_id,
        label="acc-1",
        status="active",
        storage_state={"cookies": []},
        last_error="",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = None

    created = DoubaoLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        error_text="novnc_unavailable: complete via storage_state upload",
    )

    with (
        patch(
            "aperix_geo.services.doubao_accounts.human_ops.create_login_ticket",
            return_value=created,
        ) as create_ticket,
        patch(
            "aperix_geo.services.doubao_accounts.human_ops.send_alert_email",
        ) as send_mail,
    ):
        out = request_human_intervention(
            db,
            account_id=account_id,
            reason="captcha",
            error="behavior captcha detected",
            settings=_settings(),
        )

    create_ticket.assert_called_once()
    assert out["reason"] == "captcha"
    assert out["ticket_id"] == str(created.id)
    assert out["alerted"] is True
    send_mail.assert_called_once()
    subject = send_mail.call_args.kwargs["subject"]
    assert "行为验证码" in subject
    assert "auto:captcha" in created.error_text


def test_request_human_intervention_reuses_pending_and_still_alerts() -> None:
    account_id = uuid4()
    account = DoubaoAccount(id=account_id, label="acc-1", status="active", storage_state={}, last_error="")
    pending = DoubaoLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        error_text="already open",
        login_url="https://ops.example/p/1/vnc.html",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = pending

    with (
        patch("aperix_geo.services.doubao_accounts.human_ops.create_login_ticket") as create_ticket,
        patch(
            "aperix_geo.services.doubao_accounts.human_ops.send_alert_email",
        ) as send_mail,
    ):
        out = request_human_intervention(
            db,
            account_id=account_id,
            reason="login_expired",
            error="login UI visible",
            settings=_settings(),
        )

    create_ticket.assert_not_called()
    assert out["ticket_id"] == str(pending.id)
    assert out["alerted"] is True
    send_mail.assert_called_once()
    assert "登录失效" in send_mail.call_args.kwargs["subject"]


def test_request_human_intervention_skips_ticket_when_disabled() -> None:
    account_id = uuid4()
    account = DoubaoAccount(id=account_id, label="acc-1", status="active", storage_state={}, last_error="")
    db = MagicMock()
    db.get.return_value = account

    with patch("aperix_geo.services.doubao_accounts.human_ops.create_login_ticket") as create_ticket:
        out = request_human_intervention(
            db,
            account_id=account_id,
            reason="captcha",
            error="captcha",
            settings=_settings(doubao_ops_ticket_enabled=False, provider_alert_enabled=False),
        )

    create_ticket.assert_not_called()
    assert out["ticket_id"] == ""
    assert out["alerted"] is False
    assert account.status == STATUS_NEED_RELOGIN
