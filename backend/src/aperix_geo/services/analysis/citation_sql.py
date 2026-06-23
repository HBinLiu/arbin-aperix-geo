"""SQL aggregation for citation analysis windows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponseSignal, Prompt, Subject
from aperix_geo.services.analysis._sql_daily import citation_rate, daily_citation_series
from aperix_geo.services.analysis._sql_metrics import mentioned_count_expr, with_link_count_expr
from aperix_geo.services.analysis._sql_scope import scope_where
from aperix_geo.services.analysis.entity import AnalysisEntity, list_analysis_entities


def _entity_citation_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    mentioned_expr = mentioned_count_expr()
    with_link_expr = with_link_count_expr()
    return (
        select(
            LLMResponseSignal.entity_id.label("entity_id"),
            func.sum(with_link_expr).label("with_link"),
            func.sum(mentioned_expr).label("mentioned"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(LLMResponseSignal.entity_id)
    )


def _daily_entity_citation_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    mentioned_expr = mentioned_count_expr()
    with_link_expr = with_link_count_expr()
    return (
        select(
            day_expr.label("day"),
            LLMResponseSignal.entity_id.label("entity_id"),
            func.sum(with_link_expr).label("with_link"),
            func.sum(mentioned_expr).label("mentioned"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(day_expr, LLMResponseSignal.entity_id)
        .order_by(day_expr.asc())
    )


def _share_by_label(
    rows: list[Any],
    *,
    entities: list[AnalysisEntity],
) -> tuple[dict[str, int], dict[str, float]]:
    by_entity_id = {
        str(row.entity_id): (int(row.with_link or 0), int(row.mentioned or 0)) for row in rows
    }
    counts: dict[str, int] = {}
    share: dict[str, float] = {}
    for entity in entities:
        with_link, mentioned = by_entity_id.get(entity.id, (0, 0))
        counts[entity.label] = with_link
        share[entity.label] = citation_rate(with_link, mentioned)
    return counts, share


def _daily_series_by_label(
    rows: list[Any],
    *,
    entities: list[AnalysisEntity],
) -> list[dict[str, Any]]:
    return daily_citation_series(rows, entities=entities)


def _window_has_data(db: Session, **window: Any) -> bool:
    stmt = (
        select(func.count())
        .select_from(LLMResponseSignal)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
    )
    return int(db.scalar(stmt) or 0) > 0


class _QueryCitation:
    """Patchable citation window query (tests may assign `.override`)."""

    override: Callable[..., dict[str, Any]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        prev_from: datetime,
        prev_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
        entities: list[AnalysisEntity] | None = None,
    ) -> dict[str, Any]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                prev_from=prev_from,
                prev_to=prev_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
                entities=entities,
            )
        return self._load_sql(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            prev_from=prev_from,
            prev_to=prev_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            entities=entities,
        )

    @staticmethod
    def _load_sql(
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        prev_from: datetime,
        prev_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
        entities: list[AnalysisEntity] | None = None,
    ) -> dict[str, Any]:
        catalog = entities or list_analysis_entities(subject)
        window = {
            "subject_id": subject.id,
            "platform": platform,
            "topic_id": topic_id,
            "prompt_id": prompt_id,
        }

        current_rows = db.execute(
            _entity_citation_metrics_stmt(dt_from=dt_from, dt_to=dt_to, **window)
        ).all()
        prev_rows = db.execute(
            _entity_citation_metrics_stmt(dt_from=prev_from, dt_to=prev_to, **window)
        ).all()
        current_counts, current_share = _share_by_label(current_rows, entities=catalog)
        prev_counts, prev_share = _share_by_label(prev_rows, entities=catalog)
        _ = current_counts, prev_counts

        daily_rows = db.execute(
            _daily_entity_citation_metrics_stmt(dt_from=dt_from, dt_to=dt_to, **window)
        ).all()
        prev_daily_rows = db.execute(
            _daily_entity_citation_metrics_stmt(dt_from=prev_from, dt_to=prev_to, **window)
        ).all()

        return {
            "current_share": current_share,
            "prev_share": prev_share,
            "has_previous": _window_has_data(db, dt_from=prev_from, dt_to=prev_to, **window),
            "daily_series": _daily_series_by_label(daily_rows, entities=catalog),
            "prev_daily_series": _daily_series_by_label(prev_daily_rows, entities=catalog),
        }


query_citation = _QueryCitation()
