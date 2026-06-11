"""Celery tasks: sampling pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from celery import chord, group
from sqlalchemy import select

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    SamplingJob,
    SamplingJobStatus,
)
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.llm import SamplingLLMError
from aperix_geo.services.sampling.rate_limit import SamplingRateLimitError, check_llm_rate_limit
from aperix_geo.services.sampling.retry_policy import is_retryable_sampling_error, retry_countdown_seconds
from aperix_geo.services.sampling.workflow import (
    SamplingJobError,
    enqueue_subject_sampling,
    finalize_sampling_job_db,
    find_subjects_due_for_scheduled_sampling,
    mark_response_failed,
    pending_response_id_strs,
    reconcile_stale_sampling_jobs,
    run_sample,
)
from aperix_geo.services.sampling.cache import (
    load_prompt_text_cached,
    load_subject_with_competitors_cached,
    warm_sampling_job_context,
)


def _retry_if_transient(task, exc: BaseException) -> None:
    max_retries = get_settings().sampling_retry_max
    if task.request.retries < max_retries and is_retryable_sampling_error(exc):
        raise task.retry(
            exc=exc,
            countdown=retry_countdown_seconds(task.request.retries),
        ) from exc


def _dispatch_response_chord(job_id: str, response_ids: list[str]) -> None:
    if not response_ids:
        sampling_finalize_job.apply(args=[[], job_id])
        return
    header = group(sample_one_prompt.s(response_id) for response_id in response_ids)
    chord(header)(sampling_finalize_job.s(job_id))


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sample_one_prompt(self, response_id: str) -> dict:
    """Fetch one LLMResponse row, call LLM, parse, persist."""
    rid = UUID(response_id)
    db = SessionLocal()
    try:
        row = db.get(LLMResponse, rid)
        if not row:
            return {"ok": False, "error": "missing response row"}
        if row.status != LLMResponseStatus.pending:
            return {"ok": True, "skipped": True}

        try:
            check_llm_rate_limit(row.platform)
        except SamplingRateLimitError as e:
            _retry_if_transient(self, e)
            mark_response_failed(db, row=row, error_text=str(e))
            db.commit()
            return {"ok": False, "error": str(e)}

        job = db.get(SamplingJob, row.sampling_job_id)
        if not job:
            mark_response_failed(db, row=row, error_text="missing job or prompt")
            db.commit()
            return {"ok": False}

        prompt_text = load_prompt_text_cached(db, row.prompt_id)
        if not prompt_text:
            mark_response_failed(db, row=row, error_text="missing job or prompt")
            db.commit()
            return {"ok": False}

        subject = load_subject_with_competitors_cached(db, job.subject_id)
        if not subject:
            mark_response_failed(db, row=row, error_text="missing subject")
            db.commit()
            return {"ok": False}

        try:
            run_sample(db, row=row, subject=subject, prompt_text=prompt_text)
        except SamplingLLMError as e:
            _retry_if_transient(self, e)
            mark_response_failed(db, row=row, error_text=str(e))
            db.commit()
            return {"ok": False, "error": str(e)}
        except Exception as e:
            mark_response_failed(db, row=row, error_text=str(e))
            db.commit()
            return {"ok": False, "error": str(e)}

        db.commit()
        from aperix_geo.services.brand.backfill import maybe_enqueue_brand_domain_backfill

        maybe_enqueue_brand_domain_backfill(row.id)
        return {"ok": True}
    finally:
        db.close()


@celery_app.task
def sampling_finalize_job(results: list, job_id: str) -> None:
    """Reconcile job counters and terminal status (results from chord ignored)."""
    db = SessionLocal()
    try:
        finalize_sampling_job_db(db, UUID(job_id))
    finally:
        db.close()

    from aperix_geo.tasks.favicon import warm_favicons_for_job

    warm_favicons_for_job.delay(job_id)


@celery_app.task
def sampling_orchestrate_job(job_id: str) -> None:
    """Mark running and dispatch chord of per-prompt samples."""
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(SamplingJob, jid)
        if not job:
            return
        job.status = SamplingJobStatus.running
        job.started_at = datetime.now(UTC)
        db.commit()
        response_ids = pending_response_id_strs(db, jid)
        warm_sampling_job_context(db, job_id=jid)
    finally:
        db.close()
    _dispatch_response_chord(job_id, response_ids)


@celery_app.task
def sampling_resume_pending(job_id: str, response_ids: list[str]) -> None:
    """Recovery: dispatch chord only for still-pending rows in response_ids."""
    jid = UUID(job_id)
    db = SessionLocal()
    verified: list[str] = []
    try:
        job = db.get(SamplingJob, jid)
        if not job or job.status not in (SamplingJobStatus.queued, SamplingJobStatus.running):
            return
        if job.status == SamplingJobStatus.queued:
            job.status = SamplingJobStatus.running
            if job.started_at is None:
                job.started_at = datetime.now(UTC)
            db.commit()
        requested = {UUID(response_id) for response_id in response_ids}
        verified = [
            str(response_id)
            for response_id in db.execute(
                select(LLMResponse.id).where(
                    LLMResponse.sampling_job_id == jid,
                    LLMResponse.id.in_(requested),
                    LLMResponse.status == LLMResponseStatus.pending,
                )
            ).scalars().all()
        ]
        if verified:
            warm_sampling_job_context(db, job_id=jid)
    finally:
        db.close()
    _dispatch_response_chord(job_id, verified)


@celery_app.task
def sampling_recover_stale_jobs(*, force: bool = False) -> dict:
    """Re-enqueue or finalize sampling jobs stuck in queued/running."""
    db = SessionLocal()
    try:
        recovered = reconcile_stale_sampling_jobs(db, force=force)
        return {"recovered": recovered}
    finally:
        db.close()


@celery_app.task
def sampling_scheduled_tick() -> dict:
    """Enqueue sampling jobs for subjects whose interval has elapsed."""
    db = SessionLocal()
    enqueued = 0
    skipped = 0
    errors: list[str] = []
    try:
        reconcile_stale_sampling_jobs(db)
        due_subjects = find_subjects_due_for_scheduled_sampling(db)
        for subject in due_subjects:
            try:
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
