"""Work queues for active sampling jobs (single-query aggregation)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus


@dataclass(frozen=True)
class ResponseWorkQueues:
    pending: tuple[UUID, ...]
    llm_ready: tuple[UUID, ...]
    crawl_ready: tuple[UUID, ...]

    @property
    def pending_strs(self) -> list[str]:
        return [str(response_id) for response_id in self.pending]

    @property
    def llm_ready_strs(self) -> list[str]:
        return [str(response_id) for response_id in self.llm_ready]

    @property
    def crawl_ready_strs(self) -> list[str]:
        return [str(response_id) for response_id in self.crawl_ready]

    @property
    def has_work(self) -> bool:
        return bool(self.pending or self.llm_ready or self.crawl_ready)


def response_work_queues(db: Session, job_id: UUID) -> ResponseWorkQueues:
    """Load pending / llm_ready / crawl_ready response ids in one query."""
    active = (
        LLMResponseStatus.pending,
        LLMResponseStatus.llm_ready,
        LLMResponseStatus.crawl_ready,
    )
    rows = db.execute(
        select(LLMResponse.status, LLMResponse.id).where(
            LLMResponse.sampling_job_id == job_id,
            LLMResponse.status.in_(active),
        )
    ).all()

    pending: list[UUID] = []
    llm_ready: list[UUID] = []
    crawl_ready: list[UUID] = []
    for status, response_id in rows:
        if status == LLMResponseStatus.pending:
            pending.append(response_id)
        elif status == LLMResponseStatus.llm_ready:
            llm_ready.append(response_id)
        elif status == LLMResponseStatus.crawl_ready:
            crawl_ready.append(response_id)

    return ResponseWorkQueues(
        pending=tuple(pending),
        llm_ready=tuple(llm_ready),
        crawl_ready=tuple(crawl_ready),
    )
