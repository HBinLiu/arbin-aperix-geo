"""Helpers for retrying transient PostgreSQL errors."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

T = TypeVar("T")

# 40P01 deadlock_detected; 55P03 lock_not_available
_RETRYABLE_PG_CODES = frozenset({"40P01", "55P03"})


def pg_sqlstate(exc: BaseException) -> str | None:
    orig = getattr(exc, "__cause__", None) or getattr(exc, "orig", None) or exc
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def is_retryable_db_error(exc: BaseException) -> bool:
    if not isinstance(exc, DBAPIError):
        return False
    code = pg_sqlstate(exc)
    return code in _RETRYABLE_PG_CODES if code else False


def db_retry_sleep(attempt: int) -> None:
    delay = min(0.5, 0.05 * (2**attempt)) + random.uniform(0, 0.05)
    time.sleep(delay)


def run_with_db_retry(
    db: Session,
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except DBAPIError as exc:
            last_exc = exc
            if not is_retryable_db_error(exc) or attempt >= max_attempts - 1:
                raise
            db.rollback()
            db_retry_sleep(attempt)
    assert last_exc is not None
    raise last_exc
