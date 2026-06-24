"""Enqueue Celery sampling orchestration without importing task modules."""

from __future__ import annotations

import logging
from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.services.sampling.workflow.phases import SAMPLING_DISPATCH

logger = logging.getLogger(__name__)


def enqueue_sampling_orchestration(job_id: UUID) -> None:
    from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_job_enqueue

    if not try_schedule_sampling_job_enqueue(job_id):
        logger.info("采样 orchestrate 去重跳过 job_id=%s", job_id)
        return
    celery_app.send_task(
        SAMPLING_DISPATCH,
        args=[str(job_id)],
        kwargs={"bootstrap": True},
    )


def enqueue_sampling_continue(job_id: UUID) -> None:
    """Resume fill dispatch for in-flight rows on a job."""
    celery_app.send_task(
        SAMPLING_DISPATCH,
        args=[str(job_id)],
        kwargs={"bootstrap": False},
    )
