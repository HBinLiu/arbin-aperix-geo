"""Unit tests for Doubao account pool helpers (no live Playwright)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.config import Settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, DoubaoAccount
from aperix_geo.services.doubao_accounts.heartbeat import run_doubao_account_heartbeat
from aperix_geo.services.doubao_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_NEED_RELOGIN,
    acquire_account,
    release_account,
    storage_state_has_cookies,
    upsert_account_from_state,
)


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


def test_storage_state_has_cookies() -> None:
    assert storage_state_has_cookies(_state())
    assert not storage_state_has_cookies({})
    assert not storage_state_has_cookies({"cookies": []})


def test_upsert_and_acquire_release(db_session=None) -> None:
    """In-memory style: mock Session.get / scalars chain for acquire path."""
    settings = Settings(
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
    )
    row = DoubaoAccount(
        id=uuid4(),
        label="t1",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )

    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    lease = acquire_account(db, settings=settings, lease_owner="worker-a")
    assert lease is not None
    assert lease.lease_owner == "worker-a"
    assert row.lease_owner == "worker-a"
    assert row.lease_until > utc_now()

    db.get.return_value = row
    release_account(
        db,
        account_id=row.id,
        lease_owner="worker-a",
        storage_state=_state(),
        ok=True,
    )
    assert row.lease_owner == ""
    assert row.lease_until == EPOCH
    assert row.last_ok_at > EPOCH


def test_acquire_skips_stale_account() -> None:
    settings = Settings(doubao_heartbeat_fresh_s=300, doubao_account_lease_ttl_s=300)
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    assert acquire_account(db, settings=settings) is None


@patch("aperix_geo.services.doubao_accounts.human_ops.request_human_intervention")
def test_acquire_empty_cookies_marks_need_relogin_and_opens_ticket(mock_ops: MagicMock) -> None:
    settings = Settings(
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_ops_ticket_enabled=True,
    )
    row = DoubaoAccount(
        id=uuid4(),
        label="empty",
        status=STATUS_ACTIVE,
        storage_state={},
        last_ok_at=utc_now(),
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    assert acquire_account(db, settings=settings) is None
    assert row.status == STATUS_NEED_RELOGIN
    assert "missing cookies" in row.last_error
    mock_ops.assert_called_once()
    assert mock_ops.call_args.kwargs["account_id"] == row.id
    assert mock_ops.call_args.kwargs["reason"] == "login_expired"


def test_release_marks_need_relogin_on_login_error() -> None:
    row = DoubaoAccount(
        id=uuid4(),
        label="t2",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        lease_owner="w1",
        lease_until=utc_now() + timedelta(minutes=5),
    )
    db = MagicMock()
    db.get.return_value = row
    release_account(
        db,
        account_id=row.id,
        lease_owner="w1",
        ok=False,
        error="login expired redirect",
    )
    assert row.status == STATUS_NEED_RELOGIN
    assert row.lease_owner == ""


def test_upsert_requires_cookies() -> None:
    db = MagicMock()
    with pytest.raises(ValueError):
        upsert_account_from_state(db, label="x", storage_state={"cookies": []})


def test_heartbeat_disabled_noop() -> None:
    db = MagicMock()
    result = run_doubao_account_heartbeat(db, settings=Settings(doubao_heartbeat_enabled=False))
    assert result["skipped"] is True
    db.scalars.assert_not_called()


def test_accounts_needing_heartbeat_includes_empty_cookies_even_if_fresh() -> None:
    from aperix_geo.services.doubao_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    empty = DoubaoAccount(
        id=uuid4(),
        label="empty",
        status=STATUS_ACTIVE,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    fresh_ok = DoubaoAccount(
        id=uuid4(),
        label="ok",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=now,
        lease_until=EPOCH,
    )
    stale_ok = DoubaoAccount(
        id=uuid4(),
        label="stale",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=now - timedelta(hours=4),
        lease_until=EPOCH,
    )
    selected = accounts_needing_heartbeat(
        [fresh_ok, empty, stale_ok],
        stale_before=now - timedelta(hours=3),
    )
    assert [r.label for r in selected] == ["empty", "stale"]


def test_accounts_needing_heartbeat_includes_need_relogin() -> None:
    from aperix_geo.services.doubao_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    need = DoubaoAccount(
        id=uuid4(),
        label="need",
        status=STATUS_NEED_RELOGIN,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    fresh_ok = DoubaoAccount(
        id=uuid4(),
        label="ok",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=now,
        lease_until=EPOCH,
    )
    selected = accounts_needing_heartbeat(
        [fresh_ok, need],
        stale_before=now - timedelta(hours=3),
    )
    assert [r.label for r in selected] == ["need"]
