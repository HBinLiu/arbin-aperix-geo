"""Sampling job chord orchestration (dispatch LLM / crawl / parse batches)."""

from __future__ import annotations

import logging
from uuid import UUID

from celery import chord, group

from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.active_job import load_active_job_work
from aperix_geo.services.sampling.workflow.dispatch import (
    sampling_chord_batch,
    try_schedule_sampling_chord_dispatch,
)
from aperix_geo.services.sampling.workflow.logging import log_sampling, summarize_chord_results
from aperix_geo.services.sampling.workflow.queues import response_work_queues

logger = logging.getLogger(__name__)


def dispatch_chord_batch(job_id: str, batch: list[str], *, task, finalize_task) -> bool:
    if not batch:
        return False
    if not try_schedule_sampling_chord_dispatch(UUID(job_id), batch):
        log_sampling(
            logging.WARNING,
            "采样 chord 派发跳过（job 已有在飞 chord）",
            phase="orchestrate",
            job_id=job_id,
            batch_size=len(batch),
        )
        return False
    header = group(task.s(response_id) for response_id in batch)
    chord(header)(finalize_task.s(job_id))
    return True


def dispatch_next_chord(job_id: str) -> bool:
    """Dispatch the next LLM, crawl, or parse chord batch."""
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        queues = response_work_queues(db, jid)
    finally:
        db.close()

    from aperix_geo.tasks.sampling import sampling_crawl, sampling_finalize, sampling_llm, sampling_parse

    if queues.pending:
        batch = sampling_chord_batch(queues.pending_strs)
        return dispatch_chord_batch(job_id, batch, task=sampling_llm, finalize_task=sampling_finalize)
    if queues.llm_ready:
        batch = sampling_chord_batch(queues.llm_ready_strs)
        return dispatch_chord_batch(job_id, batch, task=sampling_crawl, finalize_task=sampling_finalize)
    if queues.crawl_ready:
        batch = sampling_chord_batch(queues.crawl_ready_strs)
        return dispatch_chord_batch(job_id, batch, task=sampling_parse, finalize_task=sampling_finalize)
    return False


def run_active_job(job_id: str, *, ensure_running: bool) -> None:
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        _, pending, llm_ready, crawl_ready = load_active_job_work(db, jid, ensure_running=ensure_running)
    finally:
        db.close()

    from aperix_geo.tasks.sampling import sampling_finalize

    if not pending and not llm_ready and not crawl_ready:
        sampling_finalize.apply(args=[[], job_id])
        return
    dispatch_next_chord(job_id)


def log_finalize_batch(job_id: str, results: list) -> None:
    summary = summarize_chord_results(results)
    level = logging.INFO if summary["failed"] == 0 else logging.WARNING
    log_sampling(
        level,
        "采样 chord batch 完成",
        phase="finalize",
        job_id=job_id,
        **summary,
    )
