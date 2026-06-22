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


def summarize_chord_results(results: list) -> dict[str, int]:
    total = len(results)
    ok = 0
    skipped = 0
    failed = 0
    for item in results:
        if not isinstance(item, dict):
            failed += 1
            continue
        if item.get("skipped"):
            skipped += 1
        elif item.get("ok"):
            ok += 1
        else:
            failed += 1
    return {"total": total, "ok": ok, "skipped": skipped, "failed": failed}
