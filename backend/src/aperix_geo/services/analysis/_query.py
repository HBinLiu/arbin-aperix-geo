"""Database queries for analysis windows."""

from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Prompt, SamplingJob


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
        platforms: list[str] | None = None,
        topic_id: UUID | None = None,
        prompt_id: UUID | None = None,
    ) -> list[LLMResponse]:
        if self.override is not None:
            return self.override(
                db,
                subject_id=subject_id,
                dt_from=dt_from,
                dt_to=dt_to,
                platforms=platforms,
                topic_id=topic_id,
                prompt_id=prompt_id,
            )
        return self._query(
            db,
            subject_id=subject_id,
            dt_from=dt_from,
            dt_to=dt_to,
            platforms=platforms,
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
        platforms: list[str] | None = None,
        topic_id: UUID | None = None,
        prompt_id: UUID | None = None,
    ) -> list[LLMResponse]:
        stmt = (
            select(LLMResponse)
            .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
            .where(
                and_(
                    SamplingJob.subject_id == subject_id,
                    LLMResponse.created_at >= dt_from,
                    LLMResponse.created_at <= dt_to,
                    LLMResponse.status == LLMResponseStatus.success,
                )
            )
        )
        if platforms:
            stmt = stmt.where(LLMResponse.platform.in_(platforms))
        if topic_id is not None:
            stmt = stmt.join(Prompt, LLMResponse.prompt_id == Prompt.id).where(Prompt.topic_id == topic_id)
        if prompt_id is not None:
            stmt = stmt.where(LLMResponse.prompt_id == prompt_id)
        return [r for r in db.execute(stmt).scalars().all() if r.parsed]


responses_in_window = _ResponsesInWindowQuery()
