"""Debounce duplicate Celery orchestration per sampling job."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.cache.redis_kv import redis_set_nx_strict


def _sampling_job_enqueue_key(job_id: UUID) -> str:
    """Single debounce key for orchestrate + continue enqueue per job."""
    return f"aperix:sampling:job_enqueue:{job_id}"


def try_schedule_sampling_job_enqueue(job_id: UUID, *, force: bool = False) -> bool:
    """Return True when orchestrate/continue may be enqueued (shared Redis debounce)."""
    if force:
        return True
    settings = get_settings()
    return redis_set_nx_strict(
        _sampling_job_enqueue_key(job_id),
        ttl_s=settings.sampling_resume_debounce_seconds,
    )
