"""Sampling job finalize: debounced Celery enqueue and DB terminal state."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.schedule import commit_schedule_anchor_if_due
from aperix_geo.utils.cache.redis_kv import redis_delete, redis_set_nx_strict, shared_redis_client

logger = logging.getLogger(__name__)

SAMPLING_FINALIZE = "aperix_geo.tasks.sampling.sampling_finalize"


def _finalize_dirty_key(job_id: UUID) -> str:
    return f"aperix:sampling:finalize:{job_id}"


def _finalize_armed_key(job_id: UUID) -> str:
    return f"aperix:sampling:finalize:{job_id}:armed"


def schedule_job_finalize(job_id: UUID) -> None:
    """Trailing-debounce finalize: wait for a quiet window, then enqueue once.

    Leading-edge NX + immediate enqueue used to run finalize while items were still
    in flight; the last ``on_task_finished`` schedule then hit the same NX key and
    was dropped, leaving the job ``running`` forever after all responses succeeded.
    """
    settings = get_settings()
    debounce = max(1, settings.sampling_finalize_debounce_seconds)
    dirty_key = _finalize_dirty_key(job_id)
    armed_key = _finalize_armed_key(job_id)

    client = shared_redis_client()
    if client is not None:
        try:
            # Keep dirty longer than the countdown so a finish during the wait is visible.
            client.set(dirty_key, "1", ex=debounce + 60)
        except Exception:
            logger.debug("finalize dirty SET failed job=%s", job_id, exc_info=True)

    if not redis_set_nx_strict(armed_key, ttl_s=debounce + 5):
        return

    from aperix_geo.celery_app import celery_app

    celery_app.send_task(SAMPLING_FINALIZE, args=[str(job_id)], countdown=debounce)


def _release_finalize_arm(job_id: UUID, *, terminal: bool) -> None:
    """Allow a later schedule after this finalize run; drop dirty when job is done."""
    redis_delete(_finalize_armed_key(job_id))
    if terminal:
        redis_delete(_finalize_dirty_key(job_id))


def _response_status_counts(db: Session, job_id: UUID) -> dict[LLMResponseStatus, int]:
    rows = db.execute(
        select(LLMResponse.status, func.count(LLMResponse.id))
        .where(LLMResponse.sampling_job_id == job_id)
        .group_by(LLMResponse.status)
    ).all()
    return {status: int(count) for status, count in rows}


def release_sampling_local_caches(*, job_id: UUID | None = None) -> None:
    """Drop process-local crawl/citation L1 caches after a job becomes terminal.

    Prefork crawl/parse children keep their own L1; those rely on gzip packing and
    ``--max-tasks-per-child``. This clears the finalize worker's L1 and any shared
    job-scoped keys in the current process.
    """
    from aperix_geo.services.crawl._cache import clear_page_cache
    from aperix_geo.services.sampling.citation.cache.page_meta import (
        clear_job_citation_page_cache,
        clear_job_citation_pages_for_job,
    )

    clear_page_cache()
    if job_id is not None:
        clear_job_citation_pages_for_job(job_id)
    else:
        clear_job_citation_page_cache()


def finalize_sampling_job_db(db: Session, job_id: UUID) -> SamplingJob | None:
    """Set job counters and terminal status from response rows. Returns the job."""
    terminal = False
    try:
        job = db.execute(
            select(SamplingJob).where(SamplingJob.id == job_id).with_for_update()
        ).scalar_one_or_none()
        if not job:
            return None

        counts = _response_status_counts(db, job_id)
        ok = counts.get(LLMResponseStatus.success, 0)
        fail = counts.get(LLMResponseStatus.failed, 0)
        pending = counts.get(LLMResponseStatus.pending, 0)
        llm_ready = counts.get(LLMResponseStatus.llm_ready, 0)
        crawl_ready = counts.get(LLMResponseStatus.crawl_ready, 0)
        job.completed_items = ok
        job.failed_items = fail

        if pending or llm_ready or crawl_ready:
            # In-flight responses may still be processing; keep job active.
            job.status = SamplingJobStatus.running
            job.error_message = ""
        elif fail == 0:
            job.status = SamplingJobStatus.succeed
            job.error_message = ""
            job.finished_at = datetime.now(UTC)
        elif ok == 0:
            job.status = SamplingJobStatus.failed
            job.error_message = "All sampling items failed"
            job.finished_at = datetime.now(UTC)
        else:
            job.status = SamplingJobStatus.partial
            job.error_message = ""
            job.finished_at = datetime.now(UTC)

        terminal = job.status in (
            SamplingJobStatus.succeed,
            SamplingJobStatus.failed,
            SamplingJobStatus.partial,
        )
        if terminal:
            from aperix_geo.services.billing.quota import release_remaining_job_quota

            release_remaining_job_quota(db, job=job)

        commit_schedule_anchor_if_due(db, job)
        db.commit()
        db.refresh(job)
        if terminal:
            release_sampling_local_caches(job_id=job_id)
        return job
    finally:
        # Always drop :armed so a later on_task_finished can schedule again after an
        # early finalize that left the job running.
        _release_finalize_arm(job_id, terminal=terminal)
