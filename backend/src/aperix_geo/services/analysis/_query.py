"""Database queries for analysis windows."""

from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.base import utc_now
from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Prompt, SamplingJob, Subject


class _ResponsesInWindowQuery:
    """Patchable query hook (tests assign to `.override`)."""

    override: Callable[..., list[LLMResponse]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject_id: UUID,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
    ) -> list[LLMResponse]:
        if self.override is not None:
            return self.override(
                db,
                subject_id=subject_id,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
            )
        return self._query(
            db,
            subject_id=subject_id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
        )

    @staticmethod
    def _query(
        db: Session,
        *,
        subject_id: UUID,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
    ) -> list[LLMResponse]:
        stmt = (
            select(LLMResponse)
            .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
            .join(Prompt, LLMResponse.prompt_id == Prompt.id)
            .where(
                and_(
                    SamplingJob.subject_id == subject_id,
                    LLMResponse.created_at >= dt_from,
                    LLMResponse.created_at <= dt_to,
                    LLMResponse.status == LLMResponseStatus.success,
                )
            )
        )
        if platform:
            stmt = stmt.where(LLMResponse.platform.in_(platform))
        if topic_id:
            stmt = stmt.where(Prompt.topic_id.in_(topic_id))
        if prompt_id is not None:
            stmt = stmt.where(LLMResponse.prompt_id == prompt_id)
        return [r for r in db.execute(stmt).scalars().all() if r.parsed]


responses_in_window = _ResponsesInWindowQuery()


def response_ids_in_window_stmt(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> Select[tuple[UUID]]:
    """Success LLM responses in window (with parsed payload) — ID subquery for citation tables."""
    stmt = (
        select(LLMResponse.id)
        .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
        .join(Prompt, LLMResponse.prompt_id == Prompt.id)
        .where(
            and_(
                SamplingJob.subject_id == subject_id,
                LLMResponse.created_at >= dt_from,
                LLMResponse.created_at <= dt_to,
                LLMResponse.status == LLMResponseStatus.success,
                LLMResponse.parsed.isnot(None),
            )
        )
    )
    if platform:
        stmt = stmt.where(LLMResponse.platform.in_(platform))
    if topic_id:
        stmt = stmt.where(Prompt.topic_id.in_(topic_id))
    if prompt_id is not None:
        stmt = stmt.where(LLMResponse.prompt_id == prompt_id)
    return stmt


def count_responses_in_window(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> int:
    stmt = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    return int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def subject_response_window(db: Session, *, subject: Subject) -> tuple[datetime, datetime]:
    """Full success-response span for a subject (diagnosis center, no FilterBar window)."""
    dt_min, dt_max = db.execute(
        select(func.min(LLMResponse.created_at), func.max(LLMResponse.created_at))
        .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
        .join(Prompt, LLMResponse.prompt_id == Prompt.id)
        .where(
            and_(
                SamplingJob.subject_id == subject.id,
                LLMResponse.status == LLMResponseStatus.success,
                LLMResponse.parsed.isnot(None),
            )
        )
    ).one()
    now = utc_now()
    if dt_min is None or dt_max is None:
        return subject.created_at, now
    return dt_min, dt_max
