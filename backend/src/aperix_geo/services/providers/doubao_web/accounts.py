"""Doubao crawl credentials: file cold-start + pool lease session."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO
from aperix_geo.services.crawl_accounts.pool import (
    AccountLease,
    acquire_account,
    count_fresh_active_accounts,
    release_account,
)
from aperix_geo.services.crawl_accounts.session_cookies import (
    cookies_only_storage_state,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoLoginExpired
from aperix_geo.services.providers.doubao_web.runtime import is_human_ops_job

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_storage_state_path(settings: Settings) -> Path | None:
    raw = (settings.doubao_crawl_storage_state_path or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_file() else None


def load_storage_state_from_file(settings: Settings) -> dict | None:
    """Load Playwright storage_state JSON for cold start. None if unset/missing."""
    path = resolve_storage_state_path(settings)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DoubaoCrawlError(f"invalid storage_state file: {path}") from exc
    if not isinstance(data, dict):
        raise DoubaoCrawlError(f"storage_state must be a JSON object: {path}")
    cookies = data.get("cookies")
    if not isinstance(cookies, list) or not cookies:
        raise DoubaoLoginExpired(f"storage_state has no cookies: {path}")
    if not storage_state_has_session_cookies(data):
        raise DoubaoLoginExpired(f"storage_state missing Doubao session cookies: {path}")
    return data


def save_storage_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = cookies_only_storage_state(state)
    path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")


def crawl_credentials_available(settings: Settings, db: Session | None = None) -> bool:
    """True when file cold-start or a fresh DB account exists."""
    if resolve_storage_state_path(settings) is not None:
        return True
    if db is None:
        return False
    try:
        return count_fresh_active_accounts(db, platform=PLATFORM_DOUBAO, settings=settings) > 0
    except Exception:
        logger.debug("doubao account pool check failed", exc_info=True)
        return False


@dataclass
class DoubaoCredentialSession:
    """Owns DB session + optional pool lease for one crawl attempt."""

    db: Session
    settings: Settings
    lease: AccountLease | None = None
    storage_state: dict[str, Any] | None = None

    def acquire(self, *, use_account_pool: bool) -> dict[str, Any]:
        if use_account_pool:
            try:
                self.lease = acquire_account(
                    self.db, platform=PLATFORM_DOUBAO, settings=self.settings
                )
                if self.lease is not None:
                    self.storage_state = self.lease.storage_state
                    logger.info(
                        "doubao crawl credentials source=pool label=%s account_id=%s",
                        self.lease.label,
                        self.lease.account_id,
                    )
                self.db.commit()
            except DoubaoCrawlError:
                raise
            except Exception as exc:
                self.db.rollback()
                logger.warning("doubao account acquire failed", exc_info=True)
                self.lease = None
                raise DoubaoCrawlError("doubao account acquire failed") from exc
            if self.storage_state is None:
                raise DoubaoCrawlError(
                    "no Doubao credentials (pool empty / stale)"
                )
            return self.storage_state

        self.storage_state = load_storage_state_from_file(self.settings)
        if self.storage_state is None:
            raise DoubaoCrawlError(
                "no Doubao credentials (set DOUBAO_CRAWL_STORAGE_STATE_PATH for local smoke)"
            )
        logger.info(
            "doubao crawl credentials source=file path=%s",
            self.settings.doubao_crawl_storage_state_path,
        )
        return self.storage_state

    def request_human_ops(self, job_or_err_type: dict[str, Any] | str, err_msg: str = "") -> None:
        if self.lease is None:
            return
        from aperix_geo.services.crawl_accounts.human_ops import request_human_intervention

        if isinstance(job_or_err_type, dict):
            err_type = str(job_or_err_type.get("error_type") or "")
            err_msg = str(job_or_err_type.get("error") or err_msg or "human ops")
        else:
            err_type = job_or_err_type
        reason = "captcha" if err_type == "DoubaoCaptchaRequired" else "login_expired"
        request_human_intervention(
            self.db,
            account_id=self.lease.account_id,
            reason=reason,  # type: ignore[arg-type]
            error=err_msg,
            settings=self.settings,
        )
        self.db.commit()
        self.lease = None

    def release_ok(self, storage_state: dict[str, Any] | None) -> None:
        if self.lease is not None:
            release_account(
                self.db,
                account_id=self.lease.account_id,
                lease_owner=self.lease.lease_owner,
                storage_state=storage_state if isinstance(storage_state, dict) else None,
                ok=True,
            )
            self.db.commit()
            self.lease = None
            return
        state_path = resolve_storage_state_path(self.settings)
        if state_path is not None and isinstance(storage_state, dict):
            try:
                save_storage_state(state_path, storage_state)
            except OSError:
                logger.warning("failed to rewrite storage_state", exc_info=True)

    def release_fail(self, error: str) -> None:
        if self.lease is None:
            return
        release_account(
            self.db,
            account_id=self.lease.account_id,
            lease_owner=self.lease.lease_owner,
            ok=False,
            error=error,
        )
        self.db.commit()
        self.lease = None

    def handle_failed_job(self, job: dict[str, Any]) -> None:
        if is_human_ops_job(job):
            self.request_human_ops(job)
        else:
            self.release_fail(str(job.get("error") or "crawl failed"))

    def close(self) -> None:
        if self.lease is not None:
            try:
                self.release_fail("crawl aborted")
            except Exception:
                self.db.rollback()
                logger.warning("failed to release doubao account lease", exc_info=True)
                self.lease = None
        self.db.close()


def open_credential_session(settings: Settings) -> DoubaoCredentialSession:
    from aperix_geo.db.session import SessionLocal

    return DoubaoCredentialSession(db=SessionLocal(), settings=settings)
