"""Load LLM response signal rows for analysis windows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import EntityKind, LLMResponseSignal, Prompt, Subject


@dataclass(frozen=True)
class LLMResponseSignalRow:
    response_id: UUID
    subject_id: UUID
    prompt_id: UUID
    platform: str
    entity_id: str
    entity_kind: str
    mentioned: bool
    mention_count: int
    mention_rank: int
    sentiment_score: float
    sentiment_label: str
    has_domain_link: bool
    cited_on_source: bool
    created_at: datetime

    @classmethod
    def from_model(cls, row: LLMResponseSignal) -> LLMResponseSignalRow:
        return cls(
            response_id=row.response_id,
            subject_id=row.subject_id,
            prompt_id=row.prompt_id,
            platform=row.platform,
            entity_id=row.entity_id,
            entity_kind=row.entity_kind,
            mentioned=row.mentioned,
            mention_count=row.mention_count,
            mention_rank=row.mention_rank,
            sentiment_score=row.sentiment_score,
            sentiment_label=row.sentiment_label,
            has_domain_link=row.has_domain_link,
            cited_on_source=row.cited_on_source,
            created_at=row.created_at,
        )


def _load_llm_response_signals(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> list[LLMResponseSignalRow]:
    stmt = (
        select(LLMResponseSignal)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(
            and_(
                LLMResponseSignal.subject_id == subject.id,
                LLMResponseSignal.created_at >= dt_from,
                LLMResponseSignal.created_at <= dt_to,
                LLMResponseSignal.entity_kind.in_(
                    (EntityKind.own.value, EntityKind.competitor.value)
                ),
            )
        )
    )
    if platforms:
        stmt = stmt.where(LLMResponseSignal.platform.in_(platforms))
    if topic_id is not None:
        stmt = stmt.where(Prompt.topic_id == topic_id)
    if prompt_id is not None:
        stmt = stmt.where(LLMResponseSignal.prompt_id == prompt_id)
    if entity_id is not None:
        stmt = stmt.where(LLMResponseSignal.entity_id == entity_id)

    return [LLMResponseSignalRow.from_model(r) for r in db.execute(stmt).scalars().all()]


class _LoadLLMResponseSignals:
    """Patchable load hook (tests assign to `.override`)."""

    override: Callable[..., list[LLMResponseSignalRow]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        platforms: list[str] | None = None,
        topic_id: UUID | None = None,
        prompt_id: UUID | None = None,
        entity_id: str | None = None,
    ) -> list[LLMResponseSignalRow]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platforms=platforms,
                topic_id=topic_id,
                prompt_id=prompt_id,
                entity_id=entity_id,
            )
        return _load_llm_response_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platforms=platforms,
            topic_id=topic_id,
            prompt_id=prompt_id,
            entity_id=entity_id,
        )


load_llm_response_signals = _LoadLLMResponseSignals()
