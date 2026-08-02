"""Shared DB persist retry loop for sampling Celery tasks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import DBAPIError

from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.config import get_settings
from aperix_geo.services.sampling.retry_policy import is_retryable_sampling_error, retry_countdown_seconds
from aperix_geo.services.sampling.workflow.defer import defer_sampling_persist
from aperix_geo.utils.db_retry import db_retry_sleep, is_retryable_db_error

logger = logging.getLogger(__name__)


def retry_if_transient(task, exc: BaseException) -> None:
    from aperix_geo.services.sampling.retry_policy import is_llm_timeout_error

    if is_llm_timeout_error(exc):
        return
    max_retries = get_settings().sampling_retry_max
    if task.request.retries < max_retries and is_retryable_sampling_error(exc):
        raise task.retry(
            exc=exc,
            countdown=retry_countdown_seconds(task.request.retries),
        ) from exc


def run_persist_with_db_retry(
    task,
    db,
    *,
    sampling_job_id: UUID | None,
    phase: str,
    persist: Callable[[], bool],
    fail: Callable[[], dict],
    on_skipped: Callable[[], dict],
    on_success: Callable[[], dict] | None = None,
) -> dict:
    """Retry transient DB errors; defer or fail when retries are exhausted."""
    settings = get_settings()
    db_attempts = settings.sampling_db_retry_max
    success_result = on_success or (lambda: {"ok": True, "phase": phase})

    for attempt in range(db_attempts):
        try:
            if not persist():
                return on_skipped()
            return success_result()
        except QuotaExceededError as exc:
            # LLM persist swallows quota races; remaining phases still fail-closed.
            if phase == "llm":
                db.rollback()
                return on_skipped()
            db.rollback()
            fail()
            return {"ok": False, "error": str(exc), "quota_exhausted": True}
        except DBAPIError as exc:
            if is_retryable_db_error(exc) and attempt < db_attempts - 1:
                db.rollback()
                db_retry_sleep(attempt)
                continue
            retry_if_transient(task, exc)
            db.rollback()
            if is_retryable_db_error(exc):
                return defer_sampling_persist(
                    sampling_job_id=sampling_job_id,
                    error=str(exc),
                    phase=phase,
                )
            return fail()
        except Exception as exc:
            db.rollback()
            retry_if_transient(task, exc)
            if is_retryable_db_error(exc):
                return defer_sampling_persist(
                    sampling_job_id=sampling_job_id,
                    error=str(exc),
                    phase=phase,
                )
            return fail()

    logger.warning("采样 %s 落库本地重试耗尽 job=%s", phase, sampling_job_id)
    return defer_sampling_persist(
        sampling_job_id=sampling_job_id,
        error="db_retry_exhausted",
        phase=phase,
    )
