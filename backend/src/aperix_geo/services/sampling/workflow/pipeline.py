"""Server-sent events for live pipeline status."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from aperix_geo.db.models import Subject
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.status import (
    build_pipeline_status,
    should_close_pipeline_stream,
)

PIPELINE_STREAM_POLL_SECONDS = 2.0
PIPELINE_STREAM_HEARTBEAT_SECONDS = 15.0


class PipelineStreamAccessError(Exception):
    """Subject missing or outside tenant scope."""


def _load_pipeline_status(*, subject_id: UUID, tenant_id: UUID) -> dict[str, Any]:
    db = SessionLocal()
    try:
        subject = db.get(Subject, subject_id)
        if subject is None or subject.tenant_id != tenant_id:
            raise PipelineStreamAccessError("Subject not found")
        return build_pipeline_status(db, subject_id=subject_id)
    finally:
        db.close()


async def iter_pipeline_status_events(
    *,
    subject_id: UUID,
    tenant_id: UUID,
) -> AsyncIterator[str]:
    """Yield SSE frames until the pipeline reaches a terminal watch state."""
    last_payload: str | None = None
    loop = asyncio.get_running_loop()
    heartbeat_at = loop.time()

    while True:
        try:
            status = await asyncio.to_thread(
                _load_pipeline_status,
                subject_id=subject_id,
                tenant_id=tenant_id,
            )
        except PipelineStreamAccessError:
            yield 'event: error\ndata: {"detail":"Subject not found"}\n\n'
            return

        payload = json.dumps(status, ensure_ascii=False, separators=(",", ":"))
        if payload != last_payload:
            event = "complete" if should_close_pipeline_stream(status) else "status"
            yield f"event: {event}\ndata: {payload}\n\n"
            last_payload = payload
            if event == "complete":
                return

        now = loop.time()
        if now - heartbeat_at >= PIPELINE_STREAM_HEARTBEAT_SECONDS:
            yield ": ping\n\n"
            heartbeat_at = now

        await asyncio.sleep(PIPELINE_STREAM_POLL_SECONDS)
