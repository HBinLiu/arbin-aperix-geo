"""Defer sampling persist failures and schedule debounced recovery."""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def defer_sampling_persist(
    *,
    sampling_job_id: UUID | None,
    error: str,
    phase: str,
) -> dict:
    """Keep row state and schedule debounced continue when possible."""
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue
    from aperix_geo.services.sampling.workflow.recovery import try_schedule_sampling_resume

    logger.warning("采样落库失败，保留 %s 阶段状态以待恢复 job=%s", phase, sampling_job_id)
    if sampling_job_id is not None and try_schedule_sampling_resume(sampling_job_id):
        enqueue_sampling_continue(sampling_job_id)
    return {"ok": False, "error": error, "deferred": True, "phase": phase}
