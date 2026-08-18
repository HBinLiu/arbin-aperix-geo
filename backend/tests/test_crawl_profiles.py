"""Chrome profile path helpers + acquire skip when profile is missing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.config import Settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import EPOCH, CrawlAccount
from aperix_geo.services.crawl_accounts.pool import STATUS_ACTIVE, acquire_account
from aperix_geo.services.crawl_accounts.profiles import (
    account_profile_dir,
    job_account_fields,
    job_uses_account_profile,
    profile_is_ready,
)


def _state() -> dict:
    return {
        "cookies": [
            {
                "name": "sessionid",
                "value": "x",
                "domain": ".doubao.com",
                "path": "/",
            }
        ]
    }


def test_account_profile_dir_stable() -> None:
    aid = uuid4()
    path = account_profile_dir("doubao", aid, root="/data/crawl-profiles")
    assert path == Path("/data/crawl-profiles/doubao") / str(aid)


def test_profile_root_requires_env(monkeypatch) -> None:
    from aperix_geo.services.crawl_accounts.profiles import profile_root

    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    try:
        profile_root()
        raise AssertionError("expected missing GEO_CRAWL_PROFILE_ROOT")
    except ValueError as exc:
        assert "GEO_CRAWL_PROFILE_ROOT" in str(exc)


def test_job_account_fields_skips_zero() -> None:
    assert job_account_fields(platform="doubao", account_id=None) == {}
    assert job_account_fields(
        platform="doubao", account_id="00000000-0000-0000-0000-000000000000"
    ) == {}
    aid = uuid4()
    assert job_account_fields(platform="doubao", account_id=aid) == {
        "account_id": str(aid),
        "platform": "doubao",
    }
    assert job_uses_account_profile({"account_id": str(aid), "platform": "doubao"})
    assert not job_uses_account_profile({"storage_state": {"cookies": []}})
    from aperix_geo.services.crawl_accounts.cookies import job_payload_storage_state

    assert job_payload_storage_state({"account_id": str(aid)}) == {"cookies": []}
    assert job_payload_storage_state({"storage_state": {"cookies": [{"name": "x"}]}})[
        "cookies"
    ][0]["name"] == "x"
    assert job_payload_storage_state({}) is None


def test_profile_is_ready_requires_chrome_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert profile_is_ready(empty) is False
    ready = tmp_path / "ready"
    (ready / "Default").mkdir(parents=True)
    assert profile_is_ready(ready) is True


def test_acquire_opens_ticket_when_profile_missing(tmp_path: Path) -> None:
    settings = Settings(
        geo_crawl_profile_root=str(tmp_path),
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_crawl_timeout_s=120,
        doubao_ops_ticket_enabled=False,
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
    db.scalars.return_value.first.side_effect = [row, None]
    with patch(
        "aperix_geo.services.crawl_accounts.human_ops.request_human_intervention"
    ) as ops:
        lease = acquire_account(db, settings=settings, lease_owner="w")
    assert lease is None
    assert row.status == "need_relogin"
    ops.assert_called_once()


def test_acquire_empty_cookies_ok_when_profile_ready(tmp_path: Path) -> None:
    aid = uuid4()
    (tmp_path / "doubao" / str(aid) / "Default").mkdir(parents=True)
    settings = Settings(
        geo_crawl_profile_root=str(tmp_path),
        doubao_heartbeat_fresh_s=21600,
        doubao_account_lease_ttl_s=300,
        doubao_crawl_timeout_s=120,
        doubao_ops_ticket_enabled=False,
    )
    row = CrawlAccount(
        id=aid,
        label="t1",
        status=STATUS_ACTIVE,
        storage_state={"cookies": []},
        last_ok_at=utc_now(),
        last_error="",
        lease_owner="",
        lease_until=EPOCH,
    )
    db = MagicMock()
    db.scalars.return_value.first.return_value = row
    lease = acquire_account(db, settings=settings, lease_owner="w")
    assert lease is not None
    assert lease.account_id == aid
    assert row.status == STATUS_ACTIVE
    assert row.lease_owner == "w"
