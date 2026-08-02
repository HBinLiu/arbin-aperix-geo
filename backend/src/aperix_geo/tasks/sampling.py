"""Celery tasks: sampling pipeline."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.billing.quota import tenant_has_usable_subscription
from aperix_geo.services.billing.rollover import disable_tenant_sampling
from aperix_geo.services.sampling.workflow.active_job import run_active_job
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, enqueue_subject_sampling
from aperix_geo.services.sampling.workflow.phase import run_sampling_phase
from aperix_geo.services.sampling.workflow.phase_specs import (
    build_crawl_phase_spec,
    build_llm_phase_spec,
    build_parse_phase_spec,
)
from aperix_geo.services.sampling.workflow.recovery import recover_stale_sampling_jobs
from aperix_geo.services.sampling.workflow.schedule import find_subjects_due_for_scheduled_sampling
from aperix_geo.services.sampling.workflow.types import SamplingTaskResult

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_llm(self, response_id: str) -> SamplingTaskResult:
    """Phase 1: call platform LLM and persist raw output."""
    return run_sampling_phase(self, response_id, build_llm_phase_spec(self, response_id))


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_crawl(self, response_id: str) -> SamplingTaskResult:
    """Phase 2a: fetch citation source pages (IO-bound crawl workers)."""
    return run_sampling_phase(self, response_id, build_crawl_phase_spec(self, response_id))


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_parse(self, response_id: str) -> SamplingTaskResult:
    """Phase 2b: ABSA + citation merge from cached pages (parse workers)."""
    return run_sampling_phase(self, response_id, build_parse_phase_spec(self, response_id))


@celery_app.task(ignore_result=True)
def sampling_fill(job_id: str, phase: str) -> None:
    """Debounced refill for stream dispatch (one phase)."""
    from aperix_geo.services.sampling.workflow.fill import fill_phase

    fill_phase(job_id, phase)


def _run_sampling_finalize(job_id: str) -> None:
    if not job_id:
        logger.warning("sampling_finalize 跳过：缺少 job_id（可能是旧队列消息）")
        return
    from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db

    db = SessionLocal()
    try:
        finalize_sampling_job_db(db, UUID(job_id))
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def sampling_finalize(job_id: str = "") -> None:
    """Debounced finalize_sampling_job_db for a single job."""
    _run_sampling_finalize(job_id)


@celery_app.task(name="aperix_geo.tasks.sampling.sampling_reconcile", ignore_result=True)
def sampling_reconcile_legacy(job_id: str = "") -> None:
    """Legacy task name; forwards to sampling_finalize."""
    _run_sampling_finalize(job_id)


@celery_app.task
def sampling_dispatch(job_id: str, bootstrap: bool = True) -> None:
    """Bootstrap or resume fill dispatch for an active job."""
    run_active_job(job_id, ensure_running=bootstrap)


@celery_app.task
def sampling_orchestrate(job_id: str) -> None:
    """Legacy entry: mark running and dispatch the first fill batch."""
    run_active_job(job_id, ensure_running=True)


@celery_app.task
def sampling_continue(job_id: str) -> None:
    """Legacy entry: refill LLM / crawl / parse queues for an active job."""
    run_active_job(job_id, ensure_running=False)


@celery_app.task
def sampling_recover(*, force: bool = False) -> dict:
    """Re-enqueue or finalize sampling jobs stuck in queued/running."""
    db = SessionLocal()
    try:
        recovered = recover_stale_sampling_jobs(db, force=force)
        return {"recovered": recovered}
    finally:
        db.close()


@celery_app.task
def sampling_tick() -> dict:
    """Enqueue subjects whose hash slot has passed (only scheduled during daily window via Beat)."""
    db = SessionLocal()
    try:
        settings = get_settings()
        now = datetime.now(UTC)
        recover_stale_sampling_jobs(db)
        due_subjects = find_subjects_due_for_scheduled_sampling(db, now=now, settings=settings)
        enqueued = 0
        skipped = 0
        errors: list[str] = []
        for subject in due_subjects:
            try:
                if not tenant_has_usable_subscription(db, subject.tenant_id, now=now):
                    # Mirror expire_due_subscriptions: close the gap before status flips.
                    if subject.sampling_enabled:
                        disable_tenant_sampling(db, subject.tenant_id)
                        db.commit()
                    skipped += 1
                    continue
                enqueue_subject_sampling(
                    db,
                    subject=subject,
                    update_schedule_anchor=True,
                    validate=False,
                )
                enqueued += 1
            except SamplingJobError as e:
                skipped += 1
                errors.append(f"{subject.id}: {e}")
            except Exception as e:  # noqa: BLE001
                skipped += 1
                errors.append(f"{subject.id}: {e}")
        return {"enqueued": enqueued, "skipped": skipped, "errors": errors[:20]}
    finally:
        db.close()
