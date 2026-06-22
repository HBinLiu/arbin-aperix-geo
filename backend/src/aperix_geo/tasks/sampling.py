"""Celery tasks: sampling pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.db.models import LLMResponse, LLMResponseStatus
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.cache import (
    clear_cached_llm_result,
    load_prompt_text_cached,
    load_subject_with_competitors_cached,
)
from aperix_geo.services.sampling.llm import SamplingLLMError
from aperix_geo.services.sampling.llm_limits import SamplingRateLimitError
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.workflow.chord import (
    dispatch_next_chord,
    log_finalize_batch,
    run_active_job,
)
from aperix_geo.services.sampling.workflow.crawl import crawl_response_citations
from aperix_geo.services.sampling.workflow.execute import (
    chat_result_from_row,
    mark_response_failed,
    mark_response_failed_if_crawl_ready,
    mark_response_failed_if_llm_ready,
    mark_response_failed_if_pending,
    persist_crawl_sample,
    persist_llm_sample,
    persist_parsed_sample,
    prepare_sample_chat_result,
)
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, enqueue_subject_sampling
from aperix_geo.services.sampling.workflow.phase import SamplingPhaseSpec, run_sampling_phase
from aperix_geo.services.sampling.workflow.recovery import reconcile_stale_sampling_jobs
from aperix_geo.services.sampling.workflow.schedule import find_subjects_due_for_scheduled_sampling
from aperix_geo.services.sampling.workflow.types import SamplingTaskResult


def _fail_pending_response(db: Session, *, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_pending(db, response_id=response_id, error_text=error)
    clear_cached_llm_result(response_id)
    return {"ok": False, "error": error}


def _fail_llm_ready_response(db: Session, *, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_llm_ready(db, response_id=response_id, error_text=error)
    return {"ok": False, "error": error}


def _fail_crawl_ready_response(db: Session, *, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_crawl_ready(db, response_id=response_id, error_text=error)
    return {"ok": False, "error": error}


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_llm(self, response_id: str) -> SamplingTaskResult:
    """Phase 1: call platform LLM and persist raw output."""
    rid = UUID(response_id)
    ctx: dict[str, object] = {"response_id": rid}

    def prepare(db: Session, row: LLMResponse, job) -> SamplingTaskResult | None:
        prompt_text = load_prompt_text_cached(db, row.prompt_id)
        if not prompt_text:
            mark_response_failed(db, row=row, error_text="missing job or prompt")
            return {"ok": False, "error": "missing prompt"}
        if load_subject_with_competitors_cached(db, job.subject_id) is None:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        ctx["platform"] = row.platform
        ctx["prompt_text"] = prompt_text
        return None

    def work():
        return prepare_sample_chat_result(
            platform=str(ctx["platform"]),
            prompt_text=str(ctx["prompt_text"]),
            response_id=rid,
            cache=True,
        )

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        if isinstance(exc, SamplingRateLimitError):
            return {"ok": False, "error": str(exc), "rate_limited": True}
        if isinstance(exc, SamplingLLMError):
            mark_response_failed_if_pending(db, response_id=response_id, error_text=str(exc))
        return {"ok": False, "error": str(exc)}

    spec = SamplingPhaseSpec(
        phase="llm",
        expected_status=LLMResponseStatus.pending,
        prepare=prepare,
        work=work,
        persist=lambda db, response_id, chat_result: persist_llm_sample(
            db,
            response_id=response_id,
            chat_result=chat_result,
        ),
        fail=_fail_pending_response,
        on_skipped=lambda: (clear_cached_llm_result(rid), {"ok": True, "skipped": True, "reason": "no_longer_pending"})[1],
        on_success=lambda: (clear_cached_llm_result(rid), {"ok": True, "phase": "llm"})[1],
        on_work_error=on_work_error,
    )
    return run_sampling_phase(self, response_id, spec)


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_crawl(self, response_id: str) -> SamplingTaskResult:
    """Phase 2a: fetch citation source pages (IO-bound crawl workers)."""
    ctx: dict[str, object] = {}

    def prepare(db: Session, row: LLMResponse, job) -> SamplingTaskResult | None:
        subject = load_subject_with_competitors_cached(db, job.subject_id)
        if not subject:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        ctx["row"] = row
        ctx["subject"] = subject
        return None

    def work():
        crawl_response_citations(
            row=ctx["row"],
            subject=ctx["subject"],
            db=None,
        )

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        mark_response_failed_if_llm_ready(db, response_id=response_id, error_text=str(exc))
        return {"ok": False, "error": str(exc)}

    spec = SamplingPhaseSpec(
        phase="crawl",
        expected_status=LLMResponseStatus.llm_ready,
        prepare=prepare,
        work=work,
        persist=lambda db, response_id, _work_result: persist_crawl_sample(db, response_id=response_id),
        fail=_fail_llm_ready_response,
        on_skipped=lambda: {"ok": True, "skipped": True, "reason": "no_longer_llm_ready"},
        on_success=lambda: {"ok": True, "phase": "crawl"},
        on_work_error=on_work_error,
    )
    return run_sampling_phase(self, response_id, spec)


@celery_app.task(bind=True, max_retries=get_settings().sampling_retry_max)
def sampling_parse(self, response_id: str) -> SamplingTaskResult:
    """Phase 2b: ABSA + citation merge from cached pages (parse workers)."""
    ctx: dict[str, object] = {}

    def prepare(db: Session, row: LLMResponse, job) -> SamplingTaskResult | None:
        subject = load_subject_with_competitors_cached(db, job.subject_id)
        if not subject:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        ctx["row"] = row
        ctx["subject"] = subject
        ctx["sampling_job_id"] = row.sampling_job_id
        return None

    def work():
        row = ctx["row"]
        subject = ctx["subject"]
        chat_result = chat_result_from_row(row)
        parsed = parse_llm_output(
            chat_result.text,
            subject=subject,
            source_urls=list(chat_result.source_urls),
            web_search_mode=chat_result.web_search_mode,
            sampling_job_id=ctx["sampling_job_id"],
            db=None,
            fetch_pages=False,
        )
        return chat_result, parsed

    def persist(db: Session, response_id: UUID, work_result) -> bool:
        chat_result, parsed = work_result
        return persist_parsed_sample(
            db,
            response_id=response_id,
            subject=ctx["subject"],
            chat_result=chat_result,
            parsed=parsed,
        )

    def on_success() -> SamplingTaskResult:
        from aperix_geo.services.brand.backfill import maybe_enqueue_brand_domain_backfill

        maybe_enqueue_brand_domain_backfill(ctx["row"].id)
        return {"ok": True, "phase": "parse"}

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        mark_response_failed_if_crawl_ready(db, response_id=response_id, error_text=str(exc))
        return {"ok": False, "error": str(exc)}

    spec = SamplingPhaseSpec(
        phase="parse",
        expected_status=LLMResponseStatus.crawl_ready,
        prepare=prepare,
        work=work,
        persist=persist,
        fail=_fail_crawl_ready_response,
        on_skipped=lambda: {"ok": True, "skipped": True, "reason": "no_longer_crawl_ready"},
        on_success=on_success,
        on_work_error=on_work_error,
    )
    return run_sampling_phase(self, response_id, spec)


@celery_app.task
def sampling_finalize(results: list, job_id: str) -> None:
    """Reconcile job counters and dispatch the next chord batch when applicable."""
    from aperix_geo.services.sampling.workflow.dispatch import release_sampling_chord_dispatch

    log_finalize_batch(job_id, results)
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        finalize_sampling_job_db(db, jid)
    finally:
        db.close()

    release_sampling_chord_dispatch(jid)
    dispatch_next_chord(job_id)


@celery_app.task
def sampling_orchestrate(job_id: str) -> None:
    """Mark running and dispatch the first LLM chord batch."""
    run_active_job(job_id, ensure_running=True)


@celery_app.task
def sampling_continue(job_id: str) -> None:
    """Recovery: dispatch the next LLM, crawl, or parse chord batch for an active job."""
    run_active_job(job_id, ensure_running=False)


@celery_app.task
def sampling_recover(*, force: bool = False) -> dict:
    """Re-enqueue or finalize sampling jobs stuck in queued/running."""
    db = SessionLocal()
    try:
        recovered = reconcile_stale_sampling_jobs(db, force=force)
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
        reconcile_stale_sampling_jobs(db)
        due_subjects = find_subjects_due_for_scheduled_sampling(db, now=now, settings=settings)
        enqueued = 0
        skipped = 0
        errors: list[str] = []
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
