"""Unit tests for crawl account pool helpers (no live Playwright)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.config import Settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, CrawlAccount
from aperix_geo.services.crawl_accounts.heartbeat import run_crawl_account_heartbeat
from aperix_geo.services.crawl_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_NEED_RELOGIN,
    acquire_account,
    effective_account_lease_ttl_s,
    release_account,
    storage_state_has_cookies,
    upsert_account_from_state,
)
from aperix_geo.services.crawl_accounts.session_cookies import storage_state_has_session_cookies


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


def _guest_state() -> dict:
    return {
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
    }


def test_storage_state_requires_session_cookies() -> None:
    assert storage_state_has_cookies(_state())
    assert storage_state_has_session_cookies(_state())
    assert not storage_state_has_cookies({})
    assert not storage_state_has_cookies({"cookies": []})
    assert not storage_state_has_cookies(_guest_state())


def test_cookies_only_storage_state_drops_origins() -> None:
    from aperix_geo.services.crawl_accounts.session_cookies import cookies_only_storage_state

    fat = {
        **_state(),
        "origins": [
            {
                "origin": "https://www.doubao.com",
                "localStorage": [{"name": "text.huge", "value": "x" * 1000}],
            }
        ],
    }
    slim = cookies_only_storage_state(fat)
    assert slim == {"cookies": fat["cookies"]}
    assert "origins" not in slim


def test_effective_lease_covers_crawl_timeout() -> None:
    settings = Settings(doubao_account_lease_ttl_s=300, doubao_crawl_timeout_s=120)
    assert effective_account_lease_ttl_s(settings) == 300
    settings2 = Settings(doubao_account_lease_ttl_s=300, doubao_crawl_timeout_s=400)
    assert effective_account_lease_ttl_s(settings2) == 460  # 400 + 60


def test_upsert_and_acquire_release(db_session=None) -> None:
    """In-memory style: mock Session.get / scalars chain for acquire path."""
    settings = Settings(
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_crawl_timeout_s=120,
    )
    row = CrawlAccount(
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


@patch("aperix_geo.services.crawl_accounts.human_ops.request_human_intervention")
def test_acquire_guest_cookies_marks_need_relogin_and_tries_next(mock_ops: MagicMock) -> None:
    settings = Settings(
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_ops_ticket_enabled=True,
        doubao_crawl_timeout_s=120,
    )
    bad = CrawlAccount(
        id=uuid4(),
        label="guest",
        status=STATUS_ACTIVE,
        storage_state=_guest_state(),
        last_ok_at=utc_now(),
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    good = CrawlAccount(
        id=uuid4(),
        label="ok",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    db = MagicMock()
    db.scalars.return_value.first.side_effect = [bad, good]
    lease = acquire_account(db, settings=settings, lease_owner="w")
    assert lease is not None
    assert lease.account_id == good.id
    assert bad.status == STATUS_NEED_RELOGIN
    assert "session cookies" in bad.last_error
    mock_ops.assert_called_once()
    assert good.lease_owner == "w"


@patch("aperix_geo.services.crawl_accounts.human_ops.request_human_intervention")
def test_acquire_empty_cookies_marks_need_relogin_and_opens_ticket(mock_ops: MagicMock) -> None:
    settings = Settings(
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_ops_ticket_enabled=True,
    )
    row = CrawlAccount(
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
    # First candidate empty → ticket; second None → give up
    db.scalars.return_value.first.side_effect = [row, None]
    assert acquire_account(db, settings=settings) is None
    assert row.status == STATUS_NEED_RELOGIN
    assert "session cookies" in row.last_error
    mock_ops.assert_called_once()
    assert mock_ops.call_args.kwargs["account_id"] == row.id
    assert mock_ops.call_args.kwargs["reason"] == "login_expired"


def test_release_marks_need_relogin_on_login_error() -> None:
    row = CrawlAccount(
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


def test_upsert_requires_session_cookies() -> None:
    db = MagicMock()
    with pytest.raises(ValueError):
        upsert_account_from_state(db, label="x", storage_state={"cookies": []})
    with pytest.raises(ValueError):
        upsert_account_from_state(db, label="x", storage_state=_guest_state())


def test_heartbeat_disabled_noop() -> None:
    db = MagicMock()
    result = run_crawl_account_heartbeat(db, settings=Settings(doubao_heartbeat_enabled=False))
    assert result["skipped"] is True
    db.scalars.assert_not_called()


def test_heartbeat_success_reactivates_need_relogin() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="need",
        status=STATUS_NEED_RELOGIN,
        storage_state=_state(),
        last_ok_at=utc_now() - timedelta(days=1),
        lease_until=EPOCH,
        last_error="old",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    with patch(
        "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
        return_value=_state(),
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
        )
    assert result["ok_count"] == 1
    assert result["failed"] == 0
    assert row.status == STATUS_ACTIVE
    assert row.last_error == ""


def test_accounts_needing_heartbeat_includes_empty_cookies_even_if_fresh() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    empty = CrawlAccount(
        id=uuid4(),
        label="empty",
        status=STATUS_ACTIVE,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    fresh_ok = CrawlAccount(
        id=uuid4(),
        label="ok",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=now,
        lease_until=EPOCH,
    )
    stale_ok = CrawlAccount(
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
        now=now,
    )
    assert [r.label for r in selected] == ["empty", "stale"]


def test_accounts_needing_heartbeat_skips_leased() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    leased = CrawlAccount(
        id=uuid4(),
        label="leased",
        status=STATUS_ACTIVE,
        storage_state={},
        last_ok_at=now,
        lease_until=now + timedelta(minutes=10),
        lease_owner="w1",
    )
    need = CrawlAccount(
        id=uuid4(),
        label="need",
        status=STATUS_NEED_RELOGIN,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    selected = accounts_needing_heartbeat(
        [leased, need],
        stale_before=now - timedelta(hours=3),
        now=now,
    )
    assert [r.label for r in selected] == ["need"]


def test_accounts_needing_heartbeat_includes_need_relogin() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    need = CrawlAccount(
        id=uuid4(),
        label="need",
        status=STATUS_NEED_RELOGIN,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    fresh_ok = CrawlAccount(
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
        now=now,
    )
    assert [r.label for r in selected] == ["need"]
