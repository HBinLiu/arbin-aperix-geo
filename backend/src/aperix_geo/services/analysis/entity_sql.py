"""SQL aggregation for per-entity KPI windows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponseSignal, Prompt, Subject, SubjectType
from aperix_geo.services.analysis._sql_daily import (
    daily_citation_series,
    daily_multi_label_series,
    parse_row_day,
)
from aperix_geo.services.analysis._sql_metrics import (
    agg_metric_columns,
    mentioned_count_expr,
    with_link_count_expr,
)
from aperix_geo.services.analysis._sql_scope import scope_kwargs, scope_where
from aperix_geo.services.analysis.aggregate import (
    daily_sentiment_distribution_from_signals,
    entity_metrics_rows_from_index,
    metrics_to_dict,
    top_entity_labels_by_visibility,
)
from aperix_geo.services.analysis.entity import AnalysisEntity, list_analysis_entities
from aperix_geo.services.analysis.metrics import MetricsBundle
from aperix_geo.services.analysis.signal_index import SignalWindowIndex, build_dual_signal_window
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.sentiment import api_sentiment_label, api_sentiment_score, is_scored_sentiment


def _entity_metrics_agg_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    return (
        select(
            LLMResponseSignal.entity_id.label("entity_id"),
            *agg_metric_columns(),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(LLMResponseSignal.entity_id)
    )


def _total_voice_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    return (
        select(func.coalesce(func.sum(LLMResponseSignal.mention_count), 0).label("total_voice"))
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
    )


def _daily_entity_metrics_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    mentioned_expr = mentioned_count_expr()
    with_link_expr = with_link_count_expr()
    return (
        select(
            day_expr.label("day"),
            LLMResponseSignal.entity_id.label("entity_id"),
            func.count(func.distinct(LLMResponseSignal.response_id)).label("response_count"),
            func.sum(mentioned_expr).label("mentioned_rows"),
            func.sum(LLMResponseSignal.mention_count).label("mention_total"),
            func.sum(with_link_expr).label("mention_with_link"),
            func.avg(LLMResponseSignal.mention_rank)
            .filter(LLMResponseSignal.mention_rank > 0)
            .label("avg_rank"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(day_expr, LLMResponseSignal.entity_id)
        .order_by(day_expr.asc())
    )


def _daily_total_voice_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    return (
        select(
            day_expr.label("day"),
            func.coalesce(func.sum(LLMResponseSignal.mention_count), 0).label("total_voice"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(day_expr)
        .order_by(day_expr.asc())
    )


def _topic_entity_visibility_stmt(**window: Any) -> Select[tuple[Any, ...]]:
    return (
        select(
            Prompt.topic_id.label("topic_id"),
            LLMResponseSignal.entity_id.label("entity_id"),
            func.count(func.distinct(LLMResponseSignal.response_id)).label("response_count"),
            func.count(func.distinct(LLMResponseSignal.response_id))
            .filter(LLMResponseSignal.mentioned.is_(True))
            .label("mentioned_responses"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*scope_where(**window))
        .group_by(Prompt.topic_id, LLMResponseSignal.entity_id)
    )


def _daily_sentiment_rows_stmt(
    *,
    entity_id: str,
    **window: Any,
) -> Select[tuple[Any, ...]]:
    day_expr = func.date(LLMResponseSignal.created_at)
    label_expr = case(
        (LLMResponseSignal.sentiment_score <= 0, "negative"),
        (LLMResponseSignal.sentiment_score > 70, "positive"),
        (LLMResponseSignal.sentiment_score < 45, "negative"),
        else_="neutral",
    )
    filters = [
        *scope_where(**window),
        LLMResponseSignal.entity_id == entity_id,
        LLMResponseSignal.mentioned.is_(True),
    ]
    return (
        select(
            day_expr.label("day"),
            label_expr.label("sentiment_bucket"),
            LLMResponseSignal.platform.label("platform"),
            LLMResponseSignal.sentiment_score.label("sentiment_score"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*filters)
        .order_by(day_expr.asc())
    )


def metrics_bundle_from_agg(
    row: Any | None,
    *,
    subject: Subject,
    total_voice: int,
) -> MetricsBundle:
    if row is None or int(row.response_count or 0) == 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_rate=None,
            share_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_label=None,
            citation_coverage=None,
        )

    n = int(row.response_count or 0)
    mentioned_rows = int(row.mentioned_rows or 0)
    mention_total = int(row.mention_total or 0)
    mention_with_link = int(row.mention_with_link or 0)
    cited_on_source_rows = int(row.cited_on_source_rows or 0)
    avg_rank_raw = row.avg_rank
    avg_rank = round(float(avg_rank_raw), 2) if avg_rank_raw is not None else None
    if avg_rank is not None and not has_mention_rank(avg_rank):
        avg_rank = None

    sentiment_avg_raw = row.sentiment_avg
    if sentiment_avg_raw is not None:
        avg_sentiment = round(float(sentiment_avg_raw), 1)
    else:
        avg_sentiment = 0.0

    return MetricsBundle(
        response_count=n,
        visibility_rate=round(mentioned_rows / n, 4),
        mention_rate=round(mention_total / n, 4),
        share_voice=round(mention_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=avg_rank,
        citation_rate=round(mention_with_link / mentioned_rows, 4) if mentioned_rows > 0 else None,
        sentiment_score=avg_sentiment,
        sentiment_label=api_sentiment_label(avg_sentiment),
        citation_coverage=round(cited_on_source_rows / n, 4)
        if subject.type == SubjectType.domain or subject.website_url
        else None,
    )


def _entity_metrics_rows_from_aggs(
    aggs: list[Any],
    *,
    subject: Subject,
    entities: list[AnalysisEntity],
    total_voice: int,
) -> list[dict[str, Any]]:
    by_entity_id = {str(row.entity_id): row for row in aggs}
    rows: list[dict[str, Any]] = []
    for entity in entities:
        metrics = metrics_bundle_from_agg(
            by_entity_id.get(entity.id),
            subject=subject,
            total_voice=total_voice,
        )
        rows.append(
            {
                "id": entity.id,
                "label": entity.label,
                "brand": entity.brand or None,
                "kind": entity.kind,
                "is_own": entity.kind == "own",
                "metrics": metrics_to_dict(metrics),
            }
        )
    return rows


def _daily_share_series_from_rows(
    daily_rows: list[Any],
    *,
    entities: list[AnalysisEntity],
    daily_voice: dict[date, int],
    metric: Literal["visibility", "mention", "share_voice"],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    def value_fn(row: Any) -> float:
        n = int(row.response_count or 0)
        if n == 0:
            return 0.0
        if metric == "share_voice":
            total_voice = daily_voice.get(parse_row_day(row.day), 0)
            mention_total = int(row.mention_total or 0)
            return round(mention_total / total_voice, 4) if total_voice else 0.0
        if metric == "mention":
            return round(int(row.mention_total or 0) / n, 4)
        return round(int(row.mentioned_rows or 0) / n, 4)

    return daily_multi_label_series(
        daily_rows,
        entities=entities,
        value_fn=value_fn,
        labels=labels,
    )


def _daily_average_rank_series_from_rows(
    daily_rows: list[Any],
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for row in daily_rows:
        if str(row.entity_id) != entity_id:
            continue
        day = parse_row_day(row.day)
        avg_rank_raw = row.avg_rank
        if avg_rank_raw is None:
            value = None
        else:
            value = round(float(avg_rank_raw), 2)
            if not has_mention_rank(value):
                value = None
        series.append({"date": day.isoformat(), "value": value})
    return series


def _daily_voice_map(rows: list[Any]) -> dict[date, int]:
    out: dict[date, int] = {}
    for row in rows:
        day = parse_row_day(row.day)
        out[day] = int(row.total_voice or 0)
    return out


def _sentiment_distribution_from_rows(
    rows: list[Any],
    *,
    platform_ids: list[str] | None,
) -> list[dict[str, Any]]:
    by_day: dict[date, list[Any]] = defaultdict(list)
    for row in rows:
        day = parse_row_day(row.day)
        by_day[day].append(row)

    platform_filter = set(platform_ids) if platform_ids else None
    series: list[dict[str, Any]] = []
    for day in sorted(by_day.keys()):
        day_rows = by_day[day]
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        platform_scores: dict[str, list[float]] = defaultdict(list)
        for row in day_rows:
            bucket = str(row.sentiment_bucket or "negative")
            if bucket in counts:
                counts[bucket] += 1
            score = float(row.sentiment_score or 0)
            if is_scored_sentiment(score):
                if platform_filter is None or str(row.platform) in platform_filter:
                    platform_scores[str(row.platform)].append(api_sentiment_score(score))
        total = sum(counts.values()) or 1
        scores = [
            api_sentiment_score(float(row.sentiment_score or 0))
            for row in day_rows
            if is_scored_sentiment(float(row.sentiment_score or 0))
        ]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        point: dict[str, Any] = {
            "date": day.isoformat(),
            "positive": round(counts["positive"] / total, 4),
            "neutral": round(counts["neutral"] / total, 4),
            "negative": round(counts["negative"] / total, 4),
            "sentiment_score": avg_score,
            "sentiment_label": api_sentiment_label(avg_score),
        }
        if platform_ids:
            point["platform_scores"] = {
                platform_id: round(sum(values) / len(values), 1)
                for platform_id, values in platform_scores.items()
                if values
            }
        series.append(point)
    return series


def _topic_visibility_ranks_from_rows(
    rows: list[Any],
    *,
    subject: Subject,
    topics: dict[UUID, Any],
    limit: int,
) -> list[dict[str, Any]]:
    label_by_id = {entity.id: entity.label for entity in list_analysis_entities(subject)}
    by_topic: dict[UUID, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        topic_id = row.topic_id
        if topic_id is None:
            continue
        n = int(row.response_count or 0)
        if n == 0:
            continue
        mentioned = int(row.mentioned_responses or 0)
        rate = round(mentioned / n, 4)
        label = label_by_id.get(str(row.entity_id))
        if label:
            by_topic[topic_id].append((label, rate))

    out: list[dict[str, Any]] = []
    for topic in sorted(topics.values(), key=lambda item: item.name):
        ranked = sorted(by_topic.get(topic.id, []), key=lambda item: -item[1])
        ranks: list[str | None] = [label for label, _rate in ranked[:limit]]
        while len(ranks) < limit:
            ranks.append(None)  # type: ignore[arg-type]
        out.append(
            {
                "topic_id": str(topic.id),
                "topic_name": topic.name,
                "ranks": ranks[:limit],
            }
        )
    return out


@dataclass(frozen=True)
class EntityWindow:
    entity_rows: list[dict[str, Any]]
    total_voice: int
    daily_rows: list[Any]
    daily_voice_rows: list[Any]
    topic_visibility_rows: list[Any]
    has_data: bool


def _load_entity_window(
    db: Session,
    *,
    subject: Subject,
    entities: list[AnalysisEntity],
    window: dict[str, Any],
) -> EntityWindow:
    aggs = db.execute(_entity_metrics_agg_stmt(**window)).all()
    total_voice = int(db.scalar(_total_voice_stmt(**window)) or 0)
    daily_rows = db.execute(_daily_entity_metrics_stmt(**window)).all()
    daily_voice_rows = db.execute(_daily_total_voice_stmt(**window)).all()
    topic_visibility_rows = db.execute(_topic_entity_visibility_stmt(**window)).all()
    return EntityWindow(
        entity_rows=_entity_metrics_rows_from_aggs(
            aggs,
            subject=subject,
            entities=entities,
            total_voice=total_voice,
        ),
        total_voice=total_voice,
        daily_rows=daily_rows,
        daily_voice_rows=daily_voice_rows,
        topic_visibility_rows=topic_visibility_rows,
        has_data=bool(daily_rows),
    )


def window_overview_from_index(
    index: SignalWindowIndex,
    *,
    subject: Subject,
    entities: list[AnalysisEntity] | None = None,
) -> EntityWindow:
    catalog = entities or list_analysis_entities(subject)
    entity_rows = entity_metrics_rows_from_index(index, subject=subject, entities=catalog)
    daily_rows: list[Any] = []
    for day, day_entities in sorted(index.by_date_entity.items()):
        for entity_id, subset in day_entities.items():
            mentioned_rows = sum(1 for row in subset if row.mentioned)
            mention_total = sum(row.mention_count for row in subset)
            mention_with_link = sum(
                1 for row in subset if row.mentioned and row.has_domain_link
            )
            ranks = [float(row.mention_rank) for row in subset if has_mention_rank(row.mention_rank)]
            avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None
            daily_rows.append(
                type(
                    "DailyRow",
                    (),
                    {
                        "day": day,
                        "entity_id": entity_id,
                        "response_count": len({row.response_id for row in subset}),
                        "mentioned_rows": mentioned_rows,
                        "mention_total": mention_total,
                        "mention_with_link": mention_with_link,
                        "avg_rank": avg_rank,
                    },
                )()
            )
    daily_voice_rows = [
        type(
            "VoiceRow",
            (),
            {
                "day": day,
                "total_voice": sum(row.mention_count for row in rows),
            },
        )()
        for day, rows in sorted(index.by_date.items())
    ]
    return EntityWindow(
        entity_rows=entity_rows,
        total_voice=index.total_voice,
        daily_rows=daily_rows,
        daily_voice_rows=daily_voice_rows,
        topic_visibility_rows=[],
        has_data=bool(index.by_date),
    )


def dual_overview_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    prev_from: datetime,
    prev_to: datetime,
    entities: list[AnalysisEntity] | None = None,
) -> dict[str, EntityWindow]:
    windows = build_dual_signal_window(
        signals,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )
    catalog = entities or list_analysis_entities(subject)
    return {
        "current": window_overview_from_index(windows.current, subject=subject, entities=catalog),
        "previous": window_overview_from_index(windows.previous, subject=subject, entities=catalog),
    }


def daily_share_series_for_window(
    overview: EntityWindow,
    *,
    entities: list[AnalysisEntity],
    metric: Literal["visibility", "mention", "share_voice"],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    return _daily_share_series_from_rows(
        overview.daily_rows,
        entities=entities,
        daily_voice=_daily_voice_map(overview.daily_voice_rows),
        metric=metric,
        labels=labels,
    )


def daily_average_rank_series_for_window(
    overview: EntityWindow,
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    return _daily_average_rank_series_from_rows(overview.daily_rows, entity_id=entity_id)


def _daily_citation_share_series_from_rows(
    daily_rows: list[Any],
    *,
    entities: list[AnalysisEntity],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    return daily_citation_series(
        daily_rows,
        entities=entities,
        labels=labels,
        with_link_attr="mention_with_link",
        mentioned_attr="mentioned_rows",
    )


def daily_citation_share_series_for_window(
    overview: EntityWindow,
    *,
    entities: list[AnalysisEntity],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    return _daily_citation_share_series_from_rows(
        overview.daily_rows,
        entities=entities,
        labels=labels,
    )


def topic_visibility_ranks_for_window(
    overview: EntityWindow,
    *,
    subject: Subject,
    topics: dict[UUID, Any],
    limit: int,
) -> list[dict[str, Any]]:
    if overview.topic_visibility_rows:
        return _topic_visibility_ranks_from_rows(
            overview.topic_visibility_rows,
            subject=subject,
            topics=topics,
            limit=limit,
        )
    return []


def query_sentiment_distribution(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    platform_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    rows = db.execute(
        _daily_sentiment_rows_stmt(entity_id=entity_id, **window)
    ).all()
    return _sentiment_distribution_from_rows(rows, platform_ids=platform_ids)


class _QueryDualEntityWindow:
    """Patchable dual-window entity query (tests may assign `.override`)."""

    override: Callable[..., dict[str, EntityWindow]] | None = None

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
        brand_id: UUID | None = None,
        entities: list[AnalysisEntity] | None = None,
    ) -> dict[str, EntityWindow]:
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
                brand_id=brand_id,
                entities=entities,
            )
        catalog = entities or list_analysis_entities(subject)
        current_window = scope_kwargs(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            brand_id=brand_id,
        )
        previous_window = scope_kwargs(
            subject_id=subject.id,
            dt_from=prev_from,
            dt_to=prev_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            brand_id=brand_id,
        )
        return {
            "current": _load_entity_window(
                db, subject=subject, entities=catalog, window=current_window
            ),
            "previous": _load_entity_window(
                db, subject=subject, entities=catalog, window=previous_window
            ),
        }


class _QueryEntityWindow:
    """Patchable single-window entity overview (tests may assign `.override`)."""

    override: Callable[..., EntityWindow] | None = None

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
        brand_id: UUID | None = None,
        entities: list[AnalysisEntity] | None = None,
    ) -> EntityWindow:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
                brand_id=brand_id,
                entities=entities,
            )
        catalog = entities or list_analysis_entities(subject)
        window = scope_kwargs(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            brand_id=brand_id,
        )
        return _load_entity_window(db, subject=subject, entities=catalog, window=window)


query_dual_entity_window = _QueryDualEntityWindow()
query_entity_window = _QueryEntityWindow()

# Re-export signal-bridge helpers used by tests / topic ranks fallback.
def topic_visibility_ranks_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    prompt_to_topic: dict[UUID, UUID],
    topics: dict[UUID, Any],
    limit: int,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis.aggregate import group_signals_by_topic

    by_topic = group_signals_by_topic(signals, prompt_to_topic=prompt_to_topic)
    out: list[dict[str, Any]] = []
    for topic in sorted(topics.values(), key=lambda item: item.name):
        out.append(
            {
                "topic_id": str(topic.id),
                "topic_name": topic.name,
                "ranks": top_entity_labels_by_visibility(
                    by_topic.get(topic.id, []),
                    subject=subject,
                    limit=limit,
                ),
            }
        )
    return out


def sentiment_distribution_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    entity_id: str,
    platform_ids: list[str] | None,
) -> list[dict[str, Any]]:
    return daily_sentiment_distribution_from_signals(
        signals,
        entity_id=entity_id,
        platform_ids=platform_ids,
    )
