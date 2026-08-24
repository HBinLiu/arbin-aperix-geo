"""Tests for crawl human ops (ticket + alert) recovery path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.config import Settings
from aperix_geo.db.models import CrawlAccount, CrawlLoginTicket
from aperix_geo.services.crawl_accounts.human_ops import (
    alert_heartbeat_infra_failure,
    is_heartbeat_infra_error,
    request_human_intervention,
)
from aperix_geo.services.crawl_accounts.pool import STATUS_NEED_RELOGIN
from aperix_geo.services.crawl_accounts.tickets import TICKET_PENDING


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_ops_ticket_enabled": True,
        "doubao_ops_ticket_ttl_min": 15,
        "geo_crawl_ops_novnc_base_url": "",
        "provider_alert_enabled": True,
        "provider_alert_email_to": "ops@example.com",
        "provider_alert_cooldown_seconds": 60,
        "env": "test",
    }
    base.update(kwargs)
    return Settings(**base)


def test_request_human_intervention_opens_ticket_and_alerts() -> None:
    account_id = uuid4()
    account = CrawlAccount(
        id=account_id,
        label="acc-1",
        status="active",
        storage_state={"cookies": []},
        last_error="",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = None

    created = CrawlLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        error_text="novnc_unavailable: complete via storage_state upload",
    )

    with (
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.create_login_ticket",
            return_value=created,
        ) as create_ticket,
        patch(
            "aperix_geo.utils.cache.redis_kv.redis_set_nx",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_alert_email",
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


def test_request_human_intervention_reuses_live_session_without_alert() -> None:
    account_id = uuid4()
    account = CrawlAccount(id=account_id, label="acc-1", status="active", storage_state={}, last_error="")
    pending = CrawlLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        error_text="already open",
        login_url="https://ops.example/p/1/vnc.html",
        container_id="cid-live",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = pending

    with (
        patch("aperix_geo.services.crawl_accounts.human_ops.create_login_ticket") as create_ticket,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.ensure_pending_ticket_session",
            return_value=False,
        ) as ensure_session,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_alert_email",
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
    ensure_session.assert_called_once()
    assert out["ticket_id"] == str(pending.id)
    assert out["alerted"] is False
    send_mail.assert_not_called()


def test_request_human_intervention_respawns_dead_session_and_alerts() -> None:
    account_id = uuid4()
    account = CrawlAccount(id=account_id, label="acc-1", status="active", storage_state={}, last_error="")
    pending = CrawlLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        error_text="already open",
        login_url="https://ops.example/p/old/vnc.html",
        container_id="cid-dead",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = pending

    def _respawn(_db, ticket, **_kwargs):
        ticket.login_url = "https://ops.example/p/new/vnc.html"
        ticket.container_id = "cid-new"
        return True

    with (
        patch("aperix_geo.services.crawl_accounts.human_ops.create_login_ticket") as create_ticket,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.ensure_pending_ticket_session",
            side_effect=_respawn,
        ),
        patch(
            "aperix_geo.utils.cache.redis_kv.redis_set_nx",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_alert_email",
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
    assert out["session_refreshed"] is True
    send_mail.assert_called_once()
    assert "https://ops.example/p/new/vnc.html" in send_mail.call_args.kwargs["body"]


def test_request_human_intervention_skips_empty_url_when_novnc_configured() -> None:
    account_id = uuid4()
    account = CrawlAccount(
        id=account_id,
        label="acc-1",
        status="active",
        storage_state={"cookies": []},
        last_error="",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = None
    created = CrawlLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        login_url="",
        error_text="novnc_start_failed: HTTP 401",
    )
    with (
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.create_login_ticket",
            return_value=created,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_alert_email",
        ) as send_mail,
    ):
        out = request_human_intervention(
            db,
            account_id=account_id,
            reason="login_expired",
            error="chrome profile missing",
            settings=_settings(
                geo_web_crawl_base_url="http://127.0.0.1:9410",
                geo_crawl_ops_novnc_base_url="https://novnc.example/p/{port}/vnc.html",
            ),
        )
    assert out["ticket_id"] == str(created.id)
    assert out["alerted"] is False
    send_mail.assert_not_called()


def test_request_human_intervention_skips_ticket_when_disabled() -> None:
    account_id = uuid4()
    account = CrawlAccount(id=account_id, label="acc-1", status="active", storage_state={}, last_error="")
    db = MagicMock()
    db.get.return_value = account

    with patch("aperix_geo.services.crawl_accounts.human_ops.create_login_ticket") as create_ticket:
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


def test_request_human_intervention_debounces_repeat_alerts() -> None:
    account_id = uuid4()
    account = CrawlAccount(
        id=account_id,
        label="acc-1",
        status="active",
        storage_state={"cookies": []},
        last_error="",
    )
    db = MagicMock()
    db.get.return_value = account
    db.scalars.return_value.first.return_value = None
    created = CrawlLoginTicket(
        id=uuid4(),
        account_id=account_id,
        label="acc-1",
        token="tok",
        status=TICKET_PENDING,
        login_url="https://ops.example/p/1/vnc.html",
    )
    with (
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.create_login_ticket",
            return_value=created,
        ),
        patch(
            "aperix_geo.utils.cache.redis_kv.redis_set_nx",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_alert_email",
        ) as send_mail,
    ):
        out = request_human_intervention(
            db,
            account_id=account_id,
            reason="login_expired",
            error="login UI visible",
            settings=_settings(),
        )
    assert out["alerted"] is False
    send_mail.assert_not_called()


def test_is_heartbeat_infra_error_matches_proxy_auth() -> None:
    assert is_heartbeat_infra_error(
        "Page.goto: net::ERR_INVALID_AUTH_CREDENTIALS at https://www.doubao.com/chat/"
    )
    assert is_heartbeat_infra_error("Tunnel connection failed: 407 Proxy Authentication Required")
    assert not is_heartbeat_infra_error("page closed while waiting for generation")
    assert not is_heartbeat_infra_error("login expired")


def test_alert_heartbeat_infra_failure_emails_once() -> None:
    account_id = uuid4()
    with (
        patch(
            "aperix_geo.utils.cache.redis_kv.redis_set_nx",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_ops_alert_email",
            return_value=True,
        ) as send_mail,
    ):
        ok = alert_heartbeat_infra_failure(
            account_id=account_id,
            label="acc-proxy",
            platform="doubao",
            error="Page.goto: net::ERR_INVALID_AUTH_CREDENTIALS at https://www.doubao.com/chat/",
            settings=_settings(),
        )
    assert ok is True
    send_mail.assert_called_once()
    subject = send_mail.call_args.kwargs["subject"]
    assert "代理/网络失败" in subject
    assert "acc-proxy" in subject


def test_alert_heartbeat_infra_failure_skips_non_infra() -> None:
    with patch(
        "aperix_geo.services.crawl_accounts.human_ops.send_ops_alert_email",
    ) as send_mail:
        ok = alert_heartbeat_infra_failure(
            account_id=uuid4(),
            label="acc-1",
            platform="doubao",
            error="page closed while waiting for generation",
            settings=_settings(),
        )
    assert ok is False
    send_mail.assert_not_called()


def test_alert_heartbeat_infra_failure_debounced() -> None:
    with (
        patch(
            "aperix_geo.utils.cache.redis_kv.redis_set_nx",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.send_ops_alert_email",
        ) as send_mail,
    ):
        ok = alert_heartbeat_infra_failure(
            account_id=uuid4(),
            label="acc-1",
            platform="doubao",
            error="net::ERR_INVALID_AUTH_CREDENTIALS",
            settings=_settings(),
        )
    assert ok is False
    send_mail.assert_not_called()
