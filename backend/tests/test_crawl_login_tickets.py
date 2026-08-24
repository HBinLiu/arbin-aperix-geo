"""Tests for crawl login tickets (upload fallback; geo-web-crawl HTTP)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from aperix_geo.config import Settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, ZERO_UUID, CrawlAccount, CrawlLoginTicket
from aperix_geo.services.crawl_accounts.pool import STATUS_LOGGING_IN, STATUS_NEED_RELOGIN
from aperix_geo.services.crawl_accounts.tickets import (
    TICKET_CANCELLED,
    TICKET_EXPIRED,
    TICKET_PENDING,
    TICKET_SUCCEEDED,
    cancel_ticket,
    complete_ticket_by_token,
    complete_ticket_with_storage_state,
    create_login_ticket,
    ensure_pending_ticket_session,
    get_ticket,
    novnc_configured,
)


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_ops_ticket_enabled": True,
        "doubao_ops_ticket_ttl_min": 15,
        "geo_web_crawl_base_url": "",
        "geo_crawl_ops_novnc_base_url": "",
        "geo_crawl_ops_api_token": "ops-secret",
    }
    base.update(kwargs)
    return Settings(**base)


def _state() -> dict:
    return {
        "cookies": [
            {
                "name": "sessionid",
                "value": "x",
                "domain": ".doubao.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ],
        "origins": [],
    }


def test_novnc_configured_requires_crawl_vnc() -> None:
    assert not novnc_configured(_settings())
    assert not novnc_configured(
        _settings(
            geo_crawl_ops_novnc_base_url="https://novnc.example",
        )
    )
    assert novnc_configured(
        _settings(
            geo_web_crawl_base_url="http://127.0.0.1:9410",
            geo_crawl_ops_novnc_base_url="https://novnc.example",
        )
    )


def test_create_ticket_disabled() -> None:
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        create_login_ticket(db, label="a", settings=_settings(doubao_ops_ticket_enabled=False))
    assert exc.value.status_code == 503


def test_create_ticket_upload_fallback() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    ticket = create_login_ticket(db, label="staging-1", operator="alice", settings=_settings())
    assert ticket.status == TICKET_PENDING
    assert ticket.label == "staging-1"
    assert ticket.login_url == ""
    assert "novnc_unavailable" in ticket.error_text
    assert ticket.account_id != ZERO_UUID
    assert db.add.call_count >= 2


def test_create_ticket_with_novnc_spawn() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    with patch(
        "aperix_geo.services.crawl_accounts.tickets.start_crawl_login_session",
        return_value={
            "ok": True,
            "session_id": "crawl-login-x",
            "vnc_port": 6080,
            "watching": True,
        },
    ) as start:
        ticket = create_login_ticket(
            db,
            label="n1",
            settings=_settings(
                geo_web_crawl_base_url="http://127.0.0.1:9410",
                geo_crawl_ops_novnc_base_url="https://novnc.example",
            ),
        )
    assert ticket.login_url == f"https://novnc.example/?ticket={ticket.token}"
    assert ticket.container_id == "crawl-login-x"
    assert "crawl_login" in ticket.error_text
    start.assert_called_once()


def test_create_ticket_login_url_uses_advertised_vnc_port() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    with patch(
        "aperix_geo.services.crawl_accounts.tickets.start_crawl_login_session",
        return_value={
            "ok": True,
            "session_id": "crawl-login-x",
            "vnc_port": 6091,
            "watching": True,
        },
    ):
        ticket = create_login_ticket(
            db,
            label="n-port",
            settings=_settings(
                geo_web_crawl_base_url="http://127.0.0.1:9410",
                geo_crawl_ops_novnc_base_url="https://novnc.example/p/{port}/vnc.html",
            ),
        )
    assert ticket.login_url == "https://novnc.example/p/6091/vnc.html"


def test_ensure_pending_session_false_when_login_start_fails() -> None:
    from aperix_geo.services.crawl_browser.client import CrawlLoginClientError

    aid = uuid4()
    ticket = CrawlLoginTicket(
        id=uuid4(),
        platform="doubao",
        account_id=aid,
        label="n1",
        token="tok",
        status=TICKET_PENDING,
        container_id="",
        login_url="",
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    account = CrawlAccount(id=aid, label="n1", status=STATUS_NEED_RELOGIN, storage_state={})
    db = MagicMock()
    db.get.return_value = account
    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.crawl_login_session_running",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.start_crawl_login_session",
            side_effect=CrawlLoginClientError("HTTP 401: invalid crawl token"),
        ),
    ):
        started = ensure_pending_ticket_session(
            db,
            ticket,
            settings=_settings(
                geo_web_crawl_base_url="http://127.0.0.1:9410",
                geo_crawl_ops_novnc_base_url="https://novnc.example",
            ),
        )
    assert started is False
    assert ticket.login_url == ""
    assert ticket.status == TICKET_PENDING
    assert "novnc_start_failed" in ticket.error_text


def test_get_ticket_expires() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="x",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() - timedelta(minutes=1),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    out = get_ticket(db, ticket.id)
    assert out.status == TICKET_EXPIRED


def test_get_ticket_expires_unsticks_logging_in_account() -> None:
    aid = uuid4()
    account = CrawlAccount(
        id=aid,
        label="stuck",
        status=STATUS_LOGGING_IN,
        storage_state={},
        last_ok_at=EPOCH,
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=aid,
        label="stuck",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() - timedelta(minutes=1),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.side_effect = lambda _model, key: ticket if key == ticket.id else account
    out = get_ticket(db, ticket.id)
    assert out.status == TICKET_EXPIRED
    assert account.status == STATUS_NEED_RELOGIN


def test_cancel_ticket() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="x",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    out = cancel_ticket(db, ticket.id)
    assert out.status == TICKET_CANCELLED


def test_complete_ticket_upserts_account() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="staging-1",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    db.scalars.return_value.first.return_value = None

    out_ticket, account = complete_ticket_with_storage_state(
        db,
        ticket.id,
        storage_state=_state(),
    )
    assert out_ticket.status == TICKET_SUCCEEDED
    assert account.label == "staging-1"
    assert account.status == "active"
    db.add.assert_called()


def test_complete_ticket_does_not_stop_login_chrome() -> None:
    """Watcher is blocked on this HTTP call; stopping the thread would deadlock."""
    aid = uuid4()
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=aid,
        label="staging-1",
        token="tok",
        status=TICKET_PENDING,
        container_id=f"crawl-login:{aid}",
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    account = MagicMock()

    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.stop_crawl_login_session",
        ) as stop,
        patch(
            "aperix_geo.services.crawl_accounts.tickets._account_from_completed_ticket",
            return_value=account,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.apply_ops_handoff_lease"
        ) as handoff,
        patch(
            "aperix_geo.services.crawl_accounts.tickets._schedule_post_login_heartbeat",
        ),
    ):
        out_ticket, out_account = complete_ticket_with_storage_state(
            db,
            ticket.id,
            storage_state=_state(),
        )

    stop.assert_not_called()
    handoff.assert_called_once_with(account)
    assert out_ticket.status == TICKET_SUCCEEDED
    assert out_ticket.container_id == ""
    assert out_account is account


def test_complete_ticket_by_token() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="staging-1",
        token="tok_secret_12",
        status=TICKET_PENDING,
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.scalars.return_value.first.side_effect = [ticket, None]

    out_ticket, account = complete_ticket_by_token(
        db,
        "tok_secret_12",
        storage_state=_state(),
    )
    assert out_ticket.status == TICKET_SUCCEEDED
    assert account.status == "active"


def test_complete_rejects_guest_cookies() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="staging-1",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    with pytest.raises(HTTPException) as exc:
        complete_ticket_with_storage_state(
            db,
            ticket.id,
            storage_state={
                "cookies": [
                    {
                        "name": "odin_tt",
                        "value": "guest",
                        "domain": ".doubao.com",
                        "path": "/",
                        "expires": -1,
                        "httpOnly": False,
                        "secure": True,
                        "sameSite": "Lax",
                    }
                ],
                "origins": [],
            },
        )
    assert exc.value.status_code == 400


def test_sweep_respawns_dead_novnc_and_reopens_expired() -> None:
    from aperix_geo.services.crawl_accounts.human_ops import sweep_stale_login_tickets

    aid_dead = uuid4()
    aid_exp = uuid4()
    dead = CrawlLoginTicket(
        id=uuid4(),
        platform="doubao",
        account_id=aid_dead,
        label="dead",
        token="tok-dead",
        status=TICKET_PENDING,
        container_id=f"crawl-login:{aid_dead}",
        login_url="https://old",
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
        error_text="auto:captcha: behavior captcha detected",
    )
    expired = CrawlLoginTicket(
        id=uuid4(),
        platform="doubao",
        account_id=aid_exp,
        label="exp",
        token="tok-exp",
        status=TICKET_PENDING,
        container_id="cid-exp",
        login_url="https://old2",
        expires_at=utc_now() - timedelta(minutes=1),
        completed_at=EPOCH,
        error_text="auto:captcha: behavior captcha detected",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [dead, expired]
    settings = _settings(
        geo_web_crawl_base_url="http://127.0.0.1:9410",
        geo_crawl_ops_novnc_base_url="https://novnc.example",
    )
    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.crawl_login_session_running",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.stop_crawl_login_session",
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.start_crawl_login_session",
            return_value={
                "ok": True,
                "session_id": "crawl-login-new",
                "vnc_port": 6080,
                "watching": True,
            },
        ) as start_login,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.request_human_intervention",
        ) as reopen,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops._maybe_alert_ops",
        ) as alert,
    ):
        out = sweep_stale_login_tickets(db, settings=settings)
    assert out == {"expired": 1, "respawned": 1, "reopened": 1}
    assert dead.container_id == "crawl-login-new"
    assert dead.login_url.startswith("https://novnc.example/?ticket=")
    assert expired.status == TICKET_EXPIRED
    reopen.assert_called_once()
    assert reopen.call_args.kwargs["account_id"] == aid_exp
    assert reopen.call_args.kwargs["reason"] == "captcha"
    assert start_login.call_args.kwargs["reason"] == "captcha"
    assert alert.call_args.kwargs["reason"] == "captcha"
    alert.assert_called_once()


def test_heartbeat_sweeps_ops_even_when_probe_disabled() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import run_crawl_account_heartbeat

    db = MagicMock()
    settings = _settings(doubao_heartbeat_enabled=False, doubao_ops_ticket_enabled=True)
    with patch(
        "aperix_geo.services.crawl_accounts.human_ops.sweep_stale_login_tickets",
        return_value={"expired": 1, "respawned": 0, "reopened": 1},
    ) as sweep:
        result = run_crawl_account_heartbeat(db, settings=settings)
    assert result["skipped"] is True
    assert result["reason"] == "disabled"
    assert result["ops_sweep"]["reopened"] == 1
    sweep.assert_called_once()
    db.commit.assert_called()


def test_complete_accepts_ready_profile_without_cookies(tmp_path) -> None:
    from aperix_geo.db.models import CrawlAccount

    aid = uuid4()
    profile = tmp_path / "doubao" / str(aid) / "Default"
    profile.mkdir(parents=True)
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=aid,
        label="prod-1",
        token="tok",
        status=TICKET_PENDING,
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    account = CrawlAccount(
        id=aid,
        label="prod-1",
        platform="doubao",
        status="logging_in",
        storage_state={"cookies": []},
        last_error="",
    )
    db = MagicMock()

    def _get(model, pk):  # noqa: ANN001
        if pk == ticket.id:
            return ticket
        if pk == aid:
            return account
        return None

    db.get.side_effect = _get

    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.get_settings",
            return_value=_settings(geo_crawl_profile_root=str(tmp_path)),
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets._schedule_post_login_heartbeat",
        ) as schedule,
        patch(
            "aperix_geo.services.crawl_accounts.tickets.apply_ops_handoff_lease",
        ),
    ):
        out_ticket, out_account = complete_ticket_with_storage_state(
            db,
            ticket.id,
            storage_state={"cookies": []},
        )

    assert out_ticket.status == TICKET_SUCCEEDED
    assert out_account.status == "active"
    schedule.assert_called_once_with(aid)


def test_schedule_post_login_heartbeat_enqueues_task() -> None:
    from aperix_geo.services.crawl_accounts.tickets import _schedule_post_login_heartbeat

    aid = uuid4()
    with patch(
        "aperix_geo.tasks.crawl_accounts.crawl_account_heartbeat_account.apply_async",
    ) as apply_async:
        _schedule_post_login_heartbeat(
            aid,
            settings=_settings(doubao_heartbeat_enabled=True, doubao_ops_handoff_s=90),
        )
    apply_async.assert_called_once()
    assert apply_async.call_args.kwargs["countdown"] == 105
    assert apply_async.call_args.kwargs["args"] == [str(aid)]

