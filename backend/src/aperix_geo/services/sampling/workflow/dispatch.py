"""Debounce duplicate Celery orchestration and chord dispatches per sampling job."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.utils.cache.redis_kv import redis_set_nx


def _sampling_orchestrate_lock_key(job_id: UUID) -> str:
    return f"aperix:sampling:orchestrate:{job_id}"


def _sampling_job_chord_lock_key(job_id: UUID) -> str:
    return f"aperix:sampling:job_chord:{job_id}"


def _job_chord_lock_ttl_s() -> int:
    settings = get_settings()
    # Long enough for large jobs; scales with stale detection window.
    return min(3600, max(600, settings.sampling_stale_job_seconds * 20))


def try_schedule_sampling_orchestration_task(job_id: UUID) -> bool:
    """Return True when an orchestrate task may be enqueued for this job."""
    settings = get_settings()
    return redis_set_nx(
        _sampling_orchestrate_lock_key(job_id),
        ttl_s=settings.sampling_resume_debounce_seconds,
    )


def try_schedule_sampling_chord_dispatch(job_id: UUID, response_ids: list[str]) -> bool:
    """Return True when a chord for this job may be dispatched (one active chord per job)."""
    if not response_ids:
        return True
    return redis_set_nx(
        _sampling_job_chord_lock_key(job_id),
        ttl_s=_job_chord_lock_ttl_s(),
    )
