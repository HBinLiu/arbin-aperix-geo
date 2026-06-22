"""Enqueue Celery sampling orchestration without importing task modules."""

from __future__ import annotations

import logging
from uuid import UUID

from aperix_geo.celery_app import celery_app

logger = logging.getLogger(__name__)

SAMPLING_ORCHESTRATE = "aperix_geo.tasks.sampling.sampling_orchestrate"
SAMPLING_CONTINUE = "aperix_geo.tasks.sampling.sampling_continue"


def enqueue_sampling_orchestration(job_id: UUID) -> None:
    from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_orchestration_task

    if not try_schedule_sampling_orchestration_task(job_id):
        logger.info("采样 orchestrate 去重跳过 job_id=%s", job_id)
        return
    celery_app.send_task(SAMPLING_ORCHESTRATE, args=[str(job_id)])


def enqueue_sampling_continue(job_id: UUID) -> None:
    """Resume LLM or parse chord for in-flight rows on a job."""
    celery_app.send_task(SAMPLING_CONTINUE, args=[str(job_id)])
