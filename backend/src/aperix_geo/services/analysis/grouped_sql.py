"""SQL aggregation grouped by topic, platform, or prompt."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponseSignal, Prompt, Subject, Topic
from aperix_geo.services.analysis._sql_metrics import agg_metric_columns, mentioned_count_expr, with_link_count_expr
from aperix_geo.services.analysis._sql_scope import scope_kwargs, scope_where
from aperix_geo.services.analysis.aggregate import metrics_to_dict
from aperix_geo.services.analysis.entity_sql import metrics_bundle_from_agg

_PLATFORM_CHART_METRICS = ("visibility", "share_voice", "citation", "average_rank", "sentiment")
_METRIC_FIELDS = {
    "visibility": "visibility_rate",
    "share_voice": "share_voice",
    "citation": "citation_rate",
    "average_rank": "average_rank",
    "sentiment": "sentiment_score",
}


def _topic_entity_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    cols = agg_metric_columns()
    return (
        select(Prompt.topic_id.label("topic_id"), LLMResponseSignal.entity_id.label("entity_id"), *cols)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(Prompt.topic_id, LLMResponseSignal.entity_id)
    )


def _topic_voice_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    return (
        select(
            Prompt.topic_id.label("topic_id"),
            func.coalesce(func.sum(LLMResponseSignal.mention_count), 0).label("total_voice"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(Prompt.topic_id)
    )


def _platform_entity_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    cols = agg_metric_columns()
    return (
        select(LLMResponseSignal.platform.label("platform"), LLMResponseSignal.entity_id.label("entity_id"), *cols)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(LLMResponseSignal.platform, LLMResponseSignal.entity_id)
    )


def _topic_platform_entity_metrics_stmt(*, entity_id: str, **window: Any) -> Select[tuple[Any, ...]]:
    cols = agg_metric_columns()
    return (
        select(Prompt.topic_id.label("topic_id"), LLMResponseSignal.platform.label("platform"), *cols)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window), LLMResponseSignal.entity_id == entity_id)
        .group_by(Prompt.topic_id, LLMResponseSignal.platform)
    )


def _prompt_entity_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    cols = agg_metric_columns()
    return (
        select(LLMResponseSignal.prompt_id.label("prompt_id"), LLMResponseSignal.entity_id.label("entity_id"), *cols)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(LLMResponseSignal.prompt_id, LLMResponseSignal.entity_id)
    )


def _prompt_voice_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    return (
        select(
            LLMResponseSignal.prompt_id.label("prompt_id"),
            func.coalesce(func.sum(LLMResponseSignal.mention_count), 0).label("total_voice"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(LLMResponseSignal.prompt_id)
    )


def _daily_platform_entity_metrics_stmt(*, entity_id: str, **window: Any) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    mentioned_expr = mentioned_count_expr()
    with_link_expr = with_link_count_expr()
    return (
        select(
            day_expr.label("day"),
            LLMResponseSignal.platform.label("platform"),
            func.count(func.distinct(LLMResponseSignal.response_id)).label("response_count"),
            func.sum(mentioned_expr).label("mentioned_rows"),
            func.sum(LLMResponseSignal.mention_count).label("mention_total"),
            func.sum(with_link_expr).label("mention_with_link"),
            func.avg(LLMResponseSignal.mention_rank)
            .filter(LLMResponseSignal.mention_rank > 0)
            .label("avg_rank"),
            func.avg(LLMResponseSignal.sentiment_score)
            .filter(LLMResponseSignal.sentiment_score > 0)
            .label("sentiment_avg"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window), LLMResponseSignal.entity_id == entity_id)
        .group_by(day_expr, LLMResponseSignal.platform)
        .order_by(day_expr.asc())
    )


def _daily_platform_voice_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    return (
        select(
            day_expr.label("day"),
            LLMResponseSignal.platform.label("platform"),
            func.coalesce(func.sum(LLMResponseSignal.mention_count), 0).label("total_voice"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(day_expr, LLMResponseSignal.platform)
    )


def _parse_day(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _metrics_dict_from_row(row: Any | None, *, subject: Subject, total_voice: int) -> dict[str, Any]:
    return metrics_to_dict(metrics_bundle_from_agg(row, subject=subject, total_voice=total_voice))


def _matrix_cell(row_id: str, platform_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "platform_id": platform_id,
        "visibility_rate": metrics.get("visibility_rate"),
        "share_voice": metrics.get("share_voice"),
        "citation_rate": metrics.get("citation_rate"),
        "average_rank": metrics.get("average_rank"),
        "sentiment_score": metrics.get("sentiment_score"),
    }


def query_topic_metrics(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    topics: dict[UUID, Topic],
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> list[dict[str, Any]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    entity_rows = db.execute(_topic_entity_metrics_stmt(**window)).all()
    voice_by_topic = {
        row.topic_id: int(row.total_voice or 0)
        for row in db.execute(_topic_voice_stmt(**window)).all()
        if row.topic_id is not None
    }
    focus_by_topic = {
        row.topic_id: row for row in entity_rows if str(row.entity_id) == entity_id and row.topic_id is not None
    }
    out: list[dict[str, Any]] = []
    for tid, topic in topics.items():
        metrics = _metrics_dict_from_row(
            focus_by_topic.get(tid),
            subject=subject,
            total_voice=voice_by_topic.get(tid, 0),
        )
        if int(metrics.get("response_count") or 0) == 0:
            continue
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": topic.name,
                "visibility_rate": metrics.get("visibility_rate"),
                "mention_rate": metrics.get("mention_rate"),
                "average_rank": metrics.get("average_rank"),
                "citation_rate": metrics.get("citation_rate"),
                "sentiment_score": metrics.get("sentiment_score"),
                "sentiment_label": metrics.get("sentiment_label"),
                "response_count": metrics.get("response_count"),
            }
        )
    return sorted(out, key=lambda row: row["topic_name"])


def _query_platform_metrics(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> list[dict[str, Any]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    rows = db.execute(_platform_entity_metrics_stmt(**window)).all()
    voice_by_platform: dict[str, int] = defaultdict(int)
    for row in rows:
        voice_by_platform[str(row.platform)] += int(row.mention_total or 0)
    out: list[dict[str, Any]] = []
    for row in rows:
        if str(row.entity_id) != entity_id:
            continue
        platform_key = str(row.platform)
        metrics = _metrics_dict_from_row(
            row,
            subject=subject,
            total_voice=voice_by_platform.get(platform_key, 0),
        )
        out.append(
            {
                "platform": platform_key,
                "visibility_rate": metrics.get("visibility_rate"),
                "mention_rate": metrics.get("mention_rate"),
                "share_voice": metrics.get("share_voice"),
                "average_rank": metrics.get("average_rank"),
                "citation_rate": metrics.get("citation_rate"),
                "sentiment_score": metrics.get("sentiment_score"),
                "sentiment_label": metrics.get("sentiment_label"),
            }
        )
    return sorted(out, key=lambda row: -(row["visibility_rate"] or 0))


class _QueryPlatformMetrics:
    """Patchable platform metrics query (tests may assign `.override`)."""

    override: Callable[..., list[dict[str, Any]]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        entity_id: str,
        dt_from,
        dt_to,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                entity_id=entity_id,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
            )
        return _query_platform_metrics(
            db,
            subject=subject,
            entity_id=entity_id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
        )


query_platform_metrics = _QueryPlatformMetrics()


def query_platform_matrix(
    db: Session,
    *,
    subject: Subject,
    entities,
    focus_entity,
    platform_ids: list[str],
    row_dimension: str,
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> list[dict[str, Any]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    cells: list[dict[str, Any]] = []
    if row_dimension == "competitor":
        rows = db.execute(_platform_entity_metrics_stmt(**window)).all()
        voice_by_platform: dict[str, int] = defaultdict(int)
        for row in rows:
            voice_by_platform[str(row.platform)] += int(row.mention_total or 0)
        metrics_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            platform_key = str(row.platform)
            metrics_by_key[(platform_key, str(row.entity_id))] = _metrics_dict_from_row(
                row,
                subject=subject,
                total_voice=voice_by_platform.get(platform_key, 0),
            )
        for platform_key in platform_ids:
            for entity in entities:
                metrics = metrics_by_key.get((platform_key, entity.id), {})
                cells.append(_matrix_cell(entity.id, platform_key, metrics))
        return cells

    rows = db.execute(_topic_platform_entity_metrics_stmt(entity_id=focus_entity.id, **window)).all()
    voice_by_platform: dict[str, int] = defaultdict(int)
    for row in rows:
        voice_by_platform[str(row.platform)] += int(row.mention_total or 0)
    for platform_key in platform_ids:
        for row in rows:
            if str(row.platform) != platform_key or row.topic_id is None:
                continue
            metrics = _metrics_dict_from_row(
                row,
                subject=subject,
                total_voice=voice_by_platform.get(platform_key, 0),
            )
            cells.append(_matrix_cell(str(row.topic_id), platform_key, metrics))
    return cells


def query_platform_charts(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    platform_ids: list[str],
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    daily_rows = db.execute(_daily_platform_entity_metrics_stmt(entity_id=entity_id, **window)).all()
    voice_rows = db.execute(_daily_platform_voice_stmt(**window)).all()
    voice_by_day_platform = {
        (_parse_day(row.day), str(row.platform)): int(row.total_voice or 0) for row in voice_rows
    }
    by_day_platform = {
        (_parse_day(row.day), str(row.platform)): row for row in daily_rows
    }
    dates = sorted({key[0] for key in by_day_platform} | {key[0] for key in voice_by_day_platform})
    charts: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for metric in _PLATFORM_CHART_METRICS:
        field = _METRIC_FIELDS[metric]
        current: list[dict[str, Any]] = []
        for day in dates:
            values: dict[str, float] = {}
            for platform_key in platform_ids:
                row = by_day_platform.get((day, platform_key))
                if row is None:
                    continue
                n = int(row.response_count or 0)
                if n == 0:
                    continue
                if field == "share_voice":
                    total_voice = voice_by_day_platform.get((day, platform_key), 0)
                    mention_total = int(row.mention_total or 0)
                    value = round(mention_total / total_voice, 4) if total_voice else 0.0
                elif field == "average_rank":
                    if row.avg_rank is None:
                        continue
                    value = round(float(row.avg_rank), 2)
                elif field == "sentiment_score":
                    value = round(float(row.sentiment_avg), 1) if row.sentiment_avg is not None else 0.0
                elif field == "citation_rate":
                    mentioned = int(row.mentioned_rows or 0)
                    with_link = int(row.mention_with_link or 0)
                    value = round(with_link / mentioned, 4) if mentioned else 0.0
                else:
                    mentioned = int(row.mentioned_rows or 0)
                    value = round(mentioned / n, 4)
                values[platform_key] = value
            current.append({"date": day.isoformat(), "values": values})
        charts[metric] = {"current": current}
    return charts


def query_prompt_metrics(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    prompts: dict[UUID, Prompt],
    topics: dict[UUID, Topic],
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> list[dict[str, Any]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )
    rows = db.execute(_prompt_entity_metrics_stmt(**window)).all()
    voice_by_prompt = {
        row.prompt_id: int(row.total_voice or 0)
        for row in db.execute(_prompt_voice_stmt(**window)).all()
        if row.prompt_id is not None
    }
    out: list[dict[str, Any]] = []
    for row in rows:
        if str(row.entity_id) != entity_id or row.prompt_id is None:
            continue
        prompt = prompts.get(row.prompt_id)
        if prompt is None:
            continue
        topic = topics.get(prompt.topic_id)
        metrics = _metrics_dict_from_row(
            row,
            subject=subject,
            total_voice=voice_by_prompt.get(row.prompt_id, 0),
        )
        out.append(
            {
                "prompt_id": str(row.prompt_id),
                "prompt_text": (prompt.text[:200] if prompt.text else ""),
                "topic_id": str(prompt.topic_id) if prompt.topic_id else None,
                "topic_name": topic.name if topic else None,
                "funnel_stage": prompt.funnel_stage,
                "search_intent": prompt.search_intent,
                "visibility_rate": metrics.get("visibility_rate"),
                "mention_rate": metrics.get("mention_rate"),
                "average_rank": metrics.get("average_rank"),
                "citation_rate": metrics.get("citation_rate"),
                "sentiment_score": metrics.get("sentiment_score"),
                "sentiment_label": metrics.get("sentiment_label"),
                "response_count": metrics.get("response_count"),
            }
        )
    return out
