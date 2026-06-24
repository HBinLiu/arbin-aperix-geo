"""Structured logging helpers for the sampling pipeline."""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def _fmt_id(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def log_sampling(
    level: int,
    message: str,
    *,
    phase: str,
    response_id: UUID | str | None = None,
    job_id: UUID | str | None = None,
    **extra: object,
) -> None:
    payload = {
        "sampling_phase": phase,
        "response_id": _fmt_id(response_id),
        "job_id": _fmt_id(job_id),
        **extra,
    }
    logger.log(level, message, extra=payload)
