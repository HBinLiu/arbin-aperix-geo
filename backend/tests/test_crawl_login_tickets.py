"""Tests for crawl login tickets (upload fallback; no Docker)."""

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
    get_ticket,
    novnc_configured,
)


def _settings(**kwargs) -> Settings:
    base = {
        "doubao_ops_ticket_enabled": True,
        "doubao_ops_ticket_ttl_min": 15,
        "geo_crawl_ops_novnc_base_url": "",
        "geo_crawl_ops_docker_image": "",
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


def test_novnc_configured_requires_all_flags() -> None:
    assert not novnc_configured(_settings())
    assert novnc_configured(
        _settings(
            geo_crawl_ops_novnc_base_url="https://novnc.example",
            geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
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
    fake = MagicMock()
    fake.container_id = "cid"
    fake.login_url = "https://novnc.example/?ticket=tok"
    fake.host_port = 60123
    fake.name = "geo-crawl-ops-doubao-tok"
    with patch(
        "aperix_geo.services.crawl_accounts.tickets.spawn_ops_session",
        return_value=fake,
    ):
        ticket = create_login_ticket(
            db,
            label="n1",
            settings=_settings(
                geo_crawl_ops_novnc_base_url="https://novnc.example",
                geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
            ),
        )
    assert ticket.login_url == "https://novnc.example/?ticket=tok"
    assert ticket.container_id == "cid"
    assert "geo_crawl_ops_session" in ticket.error_text


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


def test_complete_ticket_stops_ops_before_account_is_acquirable() -> None:
    ticket = CrawlLoginTicket(
        id=uuid4(),
        account_id=ZERO_UUID,
        label="staging-1",
        token="tok",
        status=TICKET_PENDING,
        container_id="cidabc123",
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
    )
    db = MagicMock()
    db.get.return_value = ticket
    account = MagicMock()
    order: list[str] = []

    def _stop(cid: str) -> None:
        order.append(f"stop:{cid}")

    def _upsert(*_a, **_k):
        order.append("upsert")
        return account

    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.stop_ops_session",
            side_effect=_stop,
        ) as stop,
        patch(
            "aperix_geo.services.crawl_accounts.tickets.upsert_account_from_state",
            side_effect=_upsert,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.apply_ops_handoff_lease"
        ) as handoff,
    ):
        out_ticket, out_account = complete_ticket_with_storage_state(
            db,
            ticket.id,
            storage_state=_state(),
        )

    assert order == ["stop:cidabc123", "upsert"]
    stop.assert_called_once_with("cidabc123")
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
        container_id="cid-dead",
        login_url="https://old",
        expires_at=utc_now() + timedelta(minutes=10),
        completed_at=EPOCH,
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
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [dead, expired]
    settings = _settings(
        geo_crawl_ops_novnc_base_url="https://novnc.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
    )
    fake = MagicMock()
    fake.container_id = "cid-new"
    fake.login_url = "https://novnc.example/?ticket=new"
    fake.host_port = 60123
    fake.name = "geo-crawl-ops-doubao-new"
    with (
        patch(
            "aperix_geo.services.crawl_accounts.tickets.ops_session_running",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.stop_ops_session",
        ),
        patch(
            "aperix_geo.services.crawl_accounts.tickets.spawn_ops_session",
            return_value=fake,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.human_ops.request_human_intervention",
        ) as reopen,
        patch(
            "aperix_geo.services.crawl_accounts.human_ops._maybe_alert_ops",
        ) as alert,
    ):
        out = sweep_stale_login_tickets(db, settings=settings)
    assert out == {"expired": 1, "respawned": 1, "reopened": 1}
    assert dead.container_id == "cid-new"
    assert dead.login_url == "https://novnc.example/?ticket=new"
    assert expired.status == TICKET_EXPIRED
    reopen.assert_called_once()
    assert reopen.call_args.kwargs["account_id"] == aid_exp
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

