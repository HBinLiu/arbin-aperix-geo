"""Celery tasks: sampling pipeline."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

import redis
from celery import chord, group
from sqlalchemy import select

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    Prompt,
    SamplingJob,
    SamplingJobStatus,
)
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.parser import parse_llm_output
from aperix_geo.services.sampling.llm import SamplingLLMError, chat_for_platform, rate_limit_for_platform
from aperix_geo.services.subject.loader import competitor_lists, load_subject_with_competitors


def _rate_limit_check(provider: str, limit_per_minute: int) -> None:
    settings = get_settings()
    rcli = redis.from_url(settings.redis_url)
    mkey = f"aperix:llm_rl:{provider}:{int(time.time() // 60)}"
    n = rcli.incr(mkey)
    if n == 1:
        rcli.expire(mkey, 120)
    if n > limit_per_minute:
        raise RuntimeError(f"LLM rate limit exceeded for {provider}; retry scheduled.")


def _bump_job_counter(db, job_id: UUID, *, success: bool) -> None:
    job = db.get(SamplingJob, job_id)
    if not job:
        return
    if success:
        job.completed_items += 1
    else:
        job.failed_items += 1


@celery_app.task(bind=True, max_retries=8)
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
            provider, limit = rate_limit_for_platform(row.platform)
            _rate_limit_check(provider, limit)
        except (SamplingLLMError, RuntimeError) as e:
            if isinstance(e, RuntimeError):
                raise self.retry(exc=e, countdown=20) from e
            row.status = LLMResponseStatus.failed
            row.error_text = str(e)[:4000]
            _bump_job_counter(db, row.sampling_job_id, success=False)
            db.commit()
            return {"ok": False, "error": str(e)}

        job = db.get(SamplingJob, row.sampling_job_id)
        prompt = db.get(Prompt, row.prompt_id)
        if not job or not prompt:
            row.status = LLMResponseStatus.failed
            row.error_text = "missing job or prompt"
            if job:
                _bump_job_counter(db, job.id, success=False)
            db.commit()
            return {"ok": False}
        subject = load_subject_with_competitors(db, job.subject_id)
        if not subject:
            row.status = LLMResponseStatus.failed
            row.error_text = "missing subject"
            _bump_job_counter(db, job.id, success=False)
            db.commit()
            return {"ok": False}
        comp_domains, comp_brands = competitor_lists(subject)
        messages = [{"role": "user", "content": prompt.text}]
        try:
            text, usage, latency_ms = chat_for_platform(row.platform, messages)
        except SamplingLLMError as e:
            row.status = LLMResponseStatus.failed
            row.error_text = str(e)[:4000]
            _bump_job_counter(db, job.id, success=False)
            db.commit()
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            row.status = LLMResponseStatus.failed
            row.error_text = str(e)[:4000]
            _bump_job_counter(db, job.id, success=False)
            db.commit()
            return {"ok": False, "error": str(e)}

        parsed = parse_llm_output(
            text,
            subject=subject,
            competitor_domains=comp_domains,
            competitor_brands=comp_brands,
        )
        row.raw_text = text
        row.parsed = parsed
        row.usage = usage
        row.latency_ms = latency_ms
        row.status = LLMResponseStatus.success
        row.error_text = None
        _bump_job_counter(db, job.id, success=True)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@celery_app.task
def sampling_finalize_job(results: list, job_id: str) -> None:
    """Reconcile job counters and terminal status (results from chord ignored)."""
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(SamplingJob, jid)
        if not job:
            return
        rows = db.execute(select(LLMResponse).where(LLMResponse.sampling_job_id == jid)).scalars().all()
        ok = sum(1 for r in rows if r.status == LLMResponseStatus.success)
        fail = sum(1 for r in rows if r.status == LLMResponseStatus.failed)
        pending = sum(1 for r in rows if r.status == LLMResponseStatus.pending)
        job.completed_items = ok
        job.failed_items = fail
        if pending:
            job.status = SamplingJobStatus.partial
            job.error_message = f"{pending} response(s) still pending after workers finished"
        elif fail == 0:
            job.status = SamplingJobStatus.succeed
            job.error_message = None
        elif ok == 0:
            job.status = SamplingJobStatus.failed
            job.error_message = "All sampling items failed"
        else:
            job.status = SamplingJobStatus.partial
            job.error_message = None
        job.finished_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


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
        ids = [
            str(r.id)
            for r in db.execute(
                select(LLMResponse).where(
                    LLMResponse.sampling_job_id == jid,
                    LLMResponse.status == LLMResponseStatus.pending,
                )
            ).scalars().all()
        ]
    finally:
        db.close()
    if not ids:
        sampling_finalize_job.apply(args=[[], job_id])
        return
    header = group(sample_one_prompt.s(i) for i in ids)
    chord(header)(sampling_finalize_job.s(job_id))


@celery_app.task
def sampling_scheduled_tick() -> dict:
    """Enqueue sampling jobs for subjects whose interval has elapsed."""
    from aperix_geo.services.sampling.jobs import SamplingJobError, enqueue_subject_sampling
    from aperix_geo.services.sampling.schedule import find_subjects_due_for_scheduled_sampling

    db = SessionLocal()
    enqueued = 0
    skipped = 0
    errors: list[str] = []
    try:
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
