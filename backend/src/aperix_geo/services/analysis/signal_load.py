"""Load LLM response signal rows for analysis windows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import EntityKind, LLMResponseSignal, Prompt, Subject
from aperix_geo.utils.net import brand_from


@dataclass(frozen=True)
class LLMResponseSignalRow:
    response_id: UUID
    subject_id: UUID
    prompt_id: UUID
    platform: str
    entity_id: str
    entity_kind: str
    brand_id: UUID
    mentioned: bool
    mention_count: int
    mention_rank: int
    sentiment_score: float
    sentiment_reason: str
    has_domain_link: bool
    cited_on_source: bool
    created_at: datetime
    entity_label: str = ""
    primary_domain: str = ""

    @classmethod
    def from_model(cls, row: LLMResponseSignal) -> LLMResponseSignalRow:
        return cls(
            response_id=row.response_id,
            subject_id=row.subject_id,
            prompt_id=row.prompt_id,
            platform=row.platform,
            entity_id=row.entity_id,
            entity_kind=row.entity_kind,
            brand_id=row.brand_id,
            mentioned=row.mentioned,
            mention_count=row.mention_count,
            mention_rank=row.mention_rank,
            sentiment_score=row.sentiment_score,
            sentiment_reason=row.sentiment_reason,
            has_domain_link=row.has_domain_link,
            cited_on_source=row.cited_on_source,
            created_at=row.created_at,
            entity_label=row.entity_label or "",
            primary_domain=brand_from(row.primary_domain or ""),
        )


def _load_llm_response_signals(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    prompt_ids: list[UUID] | None = None,
    response_ids: list[UUID] | None = None,
    entity_id: str | None = None,
    brand_id: UUID | None = None,
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
    if platform:
        stmt = stmt.where(LLMResponseSignal.platform.in_(platform))
    if topic_id:
        stmt = stmt.where(Prompt.topic_id.in_(topic_id))
    if prompt_id is not None:
        stmt = stmt.where(LLMResponseSignal.prompt_id == prompt_id)
    elif prompt_ids:
        stmt = stmt.where(LLMResponseSignal.prompt_id.in_(prompt_ids))
    if response_ids:
        stmt = stmt.where(LLMResponseSignal.response_id.in_(response_ids))
    if brand_id is not None:
        stmt = stmt.where(LLMResponseSignal.brand_id == brand_id)
    elif entity_id is not None:
        from aperix_geo.services.brand.analysis import resolve_brand_id_for_analysis_entity

        resolved_brand_id = resolve_brand_id_for_analysis_entity(
            db,
            subject=subject,
            entity_id=entity_id,
        )
        stmt = stmt.where(LLMResponseSignal.brand_id == resolved_brand_id)

    return [LLMResponseSignalRow.from_model(r) for r in db.execute(stmt).scalars().all()]


def _load_llm_response_other_brand_signals(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    response_ids: list[UUID] | None = None,
) -> list[LLMResponseSignalRow]:
    """Open-set brand signals for ``mentioned_brands`` display (not KPI aggregation)."""
    stmt = (
        select(LLMResponseSignal)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(
            and_(
                LLMResponseSignal.subject_id == subject.id,
                LLMResponseSignal.created_at >= dt_from,
                LLMResponseSignal.created_at <= dt_to,
                LLMResponseSignal.entity_kind == EntityKind.other.value,
                LLMResponseSignal.mentioned.is_(True),
            )
        )
    )
    if platform:
        stmt = stmt.where(LLMResponseSignal.platform.in_(platform))
    if topic_id:
        stmt = stmt.where(Prompt.topic_id.in_(topic_id))
    if prompt_id is not None:
        stmt = stmt.where(LLMResponseSignal.prompt_id == prompt_id)
    if response_ids:
        stmt = stmt.where(LLMResponseSignal.response_id.in_(response_ids))

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
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
        prompt_ids: list[UUID] | None = None,
        response_ids: list[UUID] | None = None,
        entity_id: str | None = None,
        brand_id: UUID | None = None,
    ) -> list[LLMResponseSignalRow]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
                prompt_ids=prompt_ids,
                response_ids=response_ids,
                entity_id=entity_id,
                brand_id=brand_id,
            )
        return _load_llm_response_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            prompt_ids=prompt_ids,
            response_ids=response_ids,
            entity_id=entity_id,
            brand_id=brand_id,
        )


load_llm_response_signals = _LoadLLMResponseSignals()


class _LoadLLMResponseOtherBrandSignals:
    """Patchable load hook for open-set mention display."""

    override: Callable[..., list[LLMResponseSignalRow]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
        response_ids: list[UUID] | None = None,
    ) -> list[LLMResponseSignalRow]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
                response_ids=response_ids,
            )
        return _load_llm_response_other_brand_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            response_ids=response_ids,
        )


load_llm_response_other_brand_signals = _LoadLLMResponseOtherBrandSignals()


def load_mention_brand_signals(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    response_ids: list[UUID] | None = None,
) -> list[LLMResponseSignalRow]:
    """Own/competitor + open-set brand signals for ``mentioned_brands`` display."""
    return [
        *load_llm_response_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            response_ids=response_ids,
        ),
        *load_llm_response_other_brand_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            response_ids=response_ids,
        ),
    ]
