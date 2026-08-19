"""Unit tests for crawl account pool helpers (no live Playwright)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.config import Settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, CrawlAccount
from aperix_geo.services.crawl_accounts.cookies import storage_state_has_session_cookies
from aperix_geo.services.crawl_accounts.heartbeat import run_crawl_account_heartbeat
from aperix_geo.services.crawl_accounts.pool import (
    STATUS_ACTIVE,
    STATUS_NEED_RELOGIN,
    acquire_account,
    clear_account_lease,
    effective_account_lease_ttl_s,
    heartbeat_lease_ttl_s,
    release_account,
    try_lease_account,
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
    assert storage_state_has_session_cookies(_state())
    assert not storage_state_has_session_cookies({})
    assert not storage_state_has_session_cookies({"cookies": []})
    assert not storage_state_has_session_cookies(_guest_state())


def test_cookies_only_storage_state_drops_origins() -> None:
    from aperix_geo.services.crawl_accounts.cookies import cookies_only_storage_state

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


def test_keep_session_storage_state_falls_back_on_empty_export() -> None:
    from aperix_geo.services.crawl_accounts.cookies import keep_session_storage_state

    kept = keep_session_storage_state({"cookies": []}, fallback=_state())
    assert kept["cookies"][0]["name"] == "sessionid"
    fresh = keep_session_storage_state(
        {"cookies": [{"name": "sessionid", "value": "new", "domain": ".doubao.com"}]},
        fallback=_state(),
    )
    assert fresh["cookies"][0]["value"] == "new"


def test_effective_lease_covers_crawl_timeout() -> None:
    settings = Settings(doubao_account_lease_ttl_s=300, doubao_crawl_timeout_s=120)
    assert effective_account_lease_ttl_s(settings) == 300
    settings2 = Settings(doubao_account_lease_ttl_s=300, doubao_crawl_timeout_s=400)
    assert effective_account_lease_ttl_s(settings2) == 460  # 400 + 60


def test_heartbeat_lease_covers_probe_budget() -> None:
    settings = Settings(doubao_crawl_timeout_s=120, doubao_heartbeat_send_wait_s=20)
    assert heartbeat_lease_ttl_s(settings) == 140  # min(90,120)+20+30


def test_ops_handoff_lease_blocks_acquire() -> None:
    from aperix_geo.services.crawl_accounts.pool import (
        LEASE_OWNER_OPS_HANDOFF,
        apply_ops_handoff_lease,
    )

    settings = Settings(
        doubao_ops_handoff_s=90,
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
    apply_ops_handoff_lease(row, settings=settings)
    assert row.lease_owner == LEASE_OWNER_OPS_HANDOFF
    assert row.lease_until > utc_now()

    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    assert acquire_account(db, settings=settings, lease_owner="sampler") is None
    assert try_lease_account(db, account_id=row.id, lease_owner="heartbeat:x", ttl_s=90) is False
    db.scalars.return_value.first.return_value = row
    assert try_lease_account(db, account_id=row.id, lease_owner="heartbeat:x", ttl_s=90) is False


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


def test_release_fail_does_not_infer_need_relogin_from_error_text() -> None:
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
    assert row.status == STATUS_ACTIVE
    assert row.lease_owner == ""
    assert "login expired" in row.last_error


def test_release_ok_keeps_cookies_when_export_empty() -> None:
    prior = _state()
    row = CrawlAccount(
        id=uuid4(),
        label="t-keep",
        status=STATUS_ACTIVE,
        storage_state=prior,
        last_ok_at=utc_now(),
        lease_owner="w1",
        lease_until=utc_now() + timedelta(minutes=5),
        last_error="",
    )
    db = MagicMock()
    db.get.return_value = row
    release_account(
        db,
        account_id=row.id,
        lease_owner="w1",
        storage_state={"cookies": []},
        ok=True,
    )
    assert row.status == STATUS_ACTIVE
    assert row.storage_state == prior
    assert row.lease_owner == ""
    assert row.last_error == ""


def test_upsert_requires_session_cookies() -> None:
    db = MagicMock()
    with pytest.raises(ValueError):
        upsert_account_from_state(db, label="x", storage_state={"cookies": []})
    with pytest.raises(ValueError):
        upsert_account_from_state(db, label="x", storage_state=_guest_state())


def test_try_lease_account_skips_busy() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="busy",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        lease_owner="sampler",
        lease_until=utc_now() + timedelta(minutes=5),
    )
    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    assert try_lease_account(db, account_id=row.id, lease_owner="heartbeat:x", ttl_s=90) is False


def test_try_lease_account_takes_free_row() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="free",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        lease_owner="",
        lease_until=EPOCH,
    )
    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    assert try_lease_account(db, account_id=row.id, lease_owner="heartbeat:x", ttl_s=90) is True
    assert row.lease_owner == "heartbeat:x"
    assert row.lease_until > utc_now()


def test_clear_account_lease_owner_mismatch() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="busy",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now(),
        lease_owner="sampler",
        lease_until=utc_now() + timedelta(minutes=5),
    )
    db = MagicMock()
    db.get.return_value = row
    clear_account_lease(db, account_id=row.id, lease_owner="heartbeat:x")
    assert row.lease_owner == "sampler"


def test_heartbeat_disabled_noop() -> None:
    db = MagicMock()
    result = run_crawl_account_heartbeat(db, settings=Settings(doubao_heartbeat_enabled=False))
    assert result["skipped"] is True
    db.scalars.assert_not_called()


def test_heartbeat_skips_during_sampling_window() -> None:
    db = MagicMock()
    settings = Settings(
        doubao_heartbeat_enabled=True,
        sampling_daily_hour=2,
        sampling_daily_window_minutes=180,
    )
    with patch(
        "aperix_geo.services.crawl_accounts.heartbeat.in_sampling_heartbeat_quiet_window",
        return_value=True,
    ):
        result = run_crawl_account_heartbeat(db, settings=settings)
    assert result["skipped"] is True
    assert result["reason"] == "sampling_window"
    db.scalars.assert_not_called()


def test_heartbeat_manual_bypasses_sampling_quiet() -> None:
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
    db.get.return_value = row
    settings = Settings(doubao_heartbeat_enabled=True)
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.in_sampling_heartbeat_quiet_window",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            return_value=_state(),
        ),
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=settings,
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["skipped"] is False
    assert result["ok_count"] == 1


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
    db.get.return_value = row
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            return_value=_state(),
        ),
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["ok_count"] == 1
    assert result["failed"] == 0
    assert row.status == STATUS_ACTIVE
    assert row.last_error == ""


def test_heartbeat_success_without_cookie_dump_still_active() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="need",
        status=STATUS_NEED_RELOGIN,
        storage_state={},
        last_ok_at=utc_now() - timedelta(days=1),
        lease_until=EPOCH,
        last_error="old",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    db.get.return_value = row
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            return_value={"cookies": []},
        ),
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["ok_count"] == 1
    assert result["failed"] == 0
    assert row.status == STATUS_ACTIVE
    assert row.last_error == ""
    assert row.storage_state == {}


def test_heartbeat_crawl_error_does_not_mark_expired() -> None:
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError

    row = CrawlAccount(
        id=uuid4(),
        label="keep",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now() - timedelta(days=1),
        lease_until=EPOCH,
        last_error="",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    db.get.return_value = row
    old_ok = row.last_ok_at
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            side_effect=DoubaoCrawlError("page closed while waiting for generation"),
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.request_human_intervention",
        ) as mock_ops,
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.alert_heartbeat_infra_failure",
        ) as mock_infra,
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["failed"] == 1
    assert result["ok_count"] == 0
    assert row.status == STATUS_ACTIVE
    assert "page closed" in row.last_error
    mock_ops.assert_not_called()
    mock_infra.assert_called_once()
    assert row.lease_owner == ""
    assert row.last_ok_at == old_ok


def test_heartbeat_proxy_auth_error_alerts_infra() -> None:
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError

    row = CrawlAccount(
        id=uuid4(),
        label="proxy-fail",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=utc_now() - timedelta(days=1),
        lease_until=EPOCH,
        last_error="",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    db.get.return_value = row
    err = (
        "Page.goto: net::ERR_INVALID_AUTH_CREDENTIALS at "
        "https://www.doubao.com/chat/"
    )
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            side_effect=DoubaoCrawlError(err),
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.request_human_intervention",
        ) as mock_ops,
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.alert_heartbeat_infra_failure",
        ) as mock_infra,
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["failed"] == 1
    assert row.status == STATUS_ACTIVE
    mock_ops.assert_not_called()
    mock_infra.assert_called_once()
    assert "ERR_INVALID_AUTH_CREDENTIALS" in mock_infra.call_args.kwargs["error"]


def test_heartbeat_session_alive_crawl_error_touches_last_ok_at() -> None:
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError

    old_ok = utc_now() - timedelta(days=1)
    row = CrawlAccount(
        id=uuid4(),
        label="keep",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=old_ok,
        lease_until=EPOCH,
        last_error="",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    db.get.return_value = row
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
            side_effect=DoubaoCrawlError(
                "page closed while waiting for generation", session_alive=True
            ),
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.request_human_intervention",
        ) as mock_ops,
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["failed"] == 1
    assert row.status == STATUS_ACTIVE
    mock_ops.assert_not_called()
    assert row.last_ok_at > old_ok


def test_heartbeat_skips_when_lease_busy() -> None:
    row = CrawlAccount(
        id=uuid4(),
        label="busy",
        status=STATUS_NEED_RELOGIN,
        storage_state=_state(),
        last_ok_at=utc_now() - timedelta(days=1),
        lease_until=EPOCH,
        last_error="old",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.refresh = MagicMock()
    with (
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.try_lease_account",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.crawl_accounts.heartbeat.probe_account_login",
        ) as mock_probe,
    ):
        result = run_crawl_account_heartbeat(
            db,
            settings=Settings(doubao_heartbeat_enabled=True),
            platform="doubao",
            respect_sampling_quiet=False,
        )
    assert result["checked"] == 0
    assert result["skipped_leased"] == 1
    mock_probe.assert_not_called()


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


def test_accounts_needing_heartbeat_skips_empty_cookies_when_profile_ready(
    tmp_path,
) -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    aid = uuid4()
    (tmp_path / "doubao" / str(aid) / "Default").mkdir(parents=True)
    empty_ready = CrawlAccount(
        id=aid,
        label="empty-ready",
        status=STATUS_ACTIVE,
        storage_state={},
        last_ok_at=now,
        lease_until=EPOCH,
    )
    selected = accounts_needing_heartbeat(
        [empty_ready],
        stale_before=now - timedelta(hours=3),
        now=now,
        settings=Settings(geo_crawl_profile_root=str(tmp_path)),
    )
    assert selected == []


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


def test_accounts_needing_heartbeat_skips_logging_in_and_pending_ticket() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat
    from aperix_geo.services.crawl_accounts.pool import STATUS_LOGGING_IN

    now = utc_now()
    logging_in = CrawlAccount(
        id=uuid4(),
        label="vnc",
        status=STATUS_LOGGING_IN,
        storage_state=_state(),
        last_ok_at=now - timedelta(days=1),
        lease_until=EPOCH,
    )
    ticketed = CrawlAccount(
        id=uuid4(),
        label="ticketed",
        status=STATUS_NEED_RELOGIN,
        storage_state=_state(),
        last_ok_at=now - timedelta(days=1),
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
        [logging_in, ticketed, stale_ok],
        stale_before=now - timedelta(hours=3),
        now=now,
        pending_ticket_account_ids={ticketed.id},
    )
    assert [r.label for r in selected] == ["stale"]


def test_heartbeat_skips_fresh_login() -> None:
    from aperix_geo.services.crawl_accounts.heartbeat import accounts_needing_heartbeat

    now = utc_now()
    just_logged_in = CrawlAccount(
        id=uuid4(),
        label="fresh-login",
        status=STATUS_ACTIVE,
        storage_state=_state(),
        last_ok_at=now,
        lease_until=EPOCH,
    )
    selected = accounts_needing_heartbeat(
        [just_logged_in],
        now=now,
        settings=Settings(doubao_heartbeat_fresh_s=21600),
    )
    assert selected == []
