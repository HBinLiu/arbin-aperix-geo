"""Visibility analysis page — flattened payload (aligned with dashboard overview)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject, Topic
from aperix_geo.services.analysis._series import (
    TOPIC_VISIBILITY_RANK_LIMIT,
    align_previous_daily_to_current,
    align_previous_single_series,
    previous_date_range,
    slim_daily_series,
)
from aperix_geo.services.analysis.aggregate import rank_dict_from_entity_rows
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis._page import (
    build_rank_table_rows,
    metric_with_rank,
    previous_value,
)
from aperix_geo.services.analysis.entity import (
    entity_chart_labels,
    list_analysis_entities,
    own_entity,
    resolve_analysis_entity,
)
from aperix_geo.services.analysis.entity_sql import (
    daily_average_rank_series_for_window,
    daily_share_series_for_window,
    query_dual_entity_window,
    topic_visibility_ranks_for_window,
    topic_visibility_ranks_from_signals,
)
from aperix_geo.services.analysis.metrics import MetricsBundle


def _metrics_from_row(row: dict[str, Any] | None) -> MetricsBundle:
    if row is None:
        return MetricsBundle(0, None, None, None, None, None, None, None, None)
    metrics = row["metrics"]
    return MetricsBundle(
        response_count=int(metrics.get("response_count") or 0),
        visibility_rate=metrics.get("visibility_rate"),
        mention_rate=metrics.get("mention_rate"),
        share_voice=metrics.get("share_voice"),
        average_rank=metrics.get("average_rank"),
        citation_rate=metrics.get("citation_rate"),
        sentiment_score=metrics.get("sentiment_score"),
        sentiment_label=metrics.get("sentiment_label"),
        citation_coverage=metrics.get("citation_coverage"),
    )


def build_topic_visibility_ranks(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    topics: dict[UUID, Topic] | list[Topic] | None = None,
    prompt_to_topic: dict[UUID, UUID] | None = None,
) -> list[dict[str, Any]]:
    """各主题下按可见度排序的品牌 Top5（用于主题可见度排名表）。"""
    if topics is None or prompt_to_topic is None:
        topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)

    from aperix_geo.services.analysis.entity_sql import query_entity_window

    overview = query_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    topic_map = topics if isinstance(topics, dict) else {topic.id: topic for topic in topics}
    ranks = topic_visibility_ranks_for_window(
        overview,
        subject=subject,
        topics=topic_map,
        limit=TOPIC_VISIBILITY_RANK_LIMIT,
    )
    if ranks:
        return ranks

    # Fallback when SQL topic rows are empty (e.g. tests with signal override).
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    if load_llm_response_signals.override is None:
        return ranks

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    return topic_visibility_ranks_from_signals(
        all_signals,
        subject=subject,
        prompt_to_topic=prompt_to_topic,
        topics=topic_map,
        limit=TOPIC_VISIBILITY_RANK_LIMIT,
    )


def build_visibility_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """可见度页扁平化数据：四指标 KPI / 图表 / 排名表 + 主题可见度。"""
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    own = own_entity(subject)
    focus_label = entity.label

    windows = query_dual_entity_window(
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
    current = windows["current"]
    previous = windows["previous"]
    has_previous = previous.has_data

    current_entity_rows = current.entity_rows
    previous_entity_rows = previous.entity_rows
    rank = rank_dict_from_entity_rows(current_entity_rows, own_label=own.label)
    previous_rank = rank_dict_from_entity_rows(previous_entity_rows, own_label=own.label)

    focus_current_row = next((row for row in current_entity_rows if row["id"] == entity.id), None)
    focus_previous_row = next((row for row in previous_entity_rows if row["id"] == entity.id), None)
    current_metrics = _metrics_from_row(focus_current_row)
    previous_metrics = _metrics_from_row(focus_previous_row)

    series_labels = entity_chart_labels(entities)
    visibility_share = rank.get("visibility_share") or {}
    mention_share = rank.get("mention_rate") or {}
    share_voice = rank.get("share_voice") or {}
    average_rank = rank.get("average_rank") or {}

    visibility_cur = slim_daily_series(
        daily_share_series_for_window(
            current,
            entities=entities,
            metric="visibility",
            labels=series_labels,
        ),
        series_labels,
    )
    mention_cur = slim_daily_series(
        daily_share_series_for_window(
            current,
            entities=entities,
            metric="mention",
            labels=series_labels,
        ),
        series_labels,
    )
    average_rank_cur = daily_average_rank_series_for_window(current, entity_id=entity.id)

    if has_previous:
        visibility_pre = align_previous_daily_to_current(
            visibility_cur,
            daily_share_series_for_window(
                previous,
                entities=entities,
                metric="visibility",
                labels=[focus_label],
            ),
            [focus_label],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        )
        mention_pre = align_previous_daily_to_current(
            mention_cur,
            daily_share_series_for_window(
                previous,
                entities=entities,
                metric="mention",
                labels=[focus_label],
            ),
            [focus_label],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        )
        average_rank_pre = align_previous_single_series(
            average_rank_cur,
            daily_average_rank_series_for_window(previous, entity_id=entity.id),
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        )
    else:
        visibility_pre = [
            {"date": pt["date"], "values": {focus_label: None}} for pt in visibility_cur
        ]
        mention_pre = [{"date": pt["date"], "values": {focus_label: None}} for pt in mention_cur]
        average_rank_pre = [{"date": pt["date"], "value": None} for pt in average_rank_cur]

    topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
    topic_visibility_ranks = build_topic_visibility_ranks(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        topics=topics,
        prompt_to_topic=prompt_to_topic,
    )

    table_kwargs = {
        "entities": entities,
        "has_previous": has_previous,
    }

    return {
        "entity_id": entity.id,
        "visibility": metric_with_rank(
            current_metrics.visibility_rate,
            previous_value(previous_metrics.visibility_rate, has_previous=has_previous),
            visibility_share,
            focus_label,
        ),
        "mention": metric_with_rank(
            current_metrics.mention_rate,
            previous_value(previous_metrics.mention_rate, has_previous=has_previous),
            mention_share,
            focus_label,
        ),
        "share_voice": metric_with_rank(
            current_metrics.share_voice,
            previous_value(previous_metrics.share_voice, has_previous=has_previous),
            share_voice,
            focus_label,
        ),
        "average_rank": metric_with_rank(
            current_metrics.average_rank,
            previous_value(previous_metrics.average_rank, has_previous=has_previous),
            average_rank,
            focus_label,
        ),
        "visibility_chart": {
            "cur_series": visibility_cur,
            "pre_series": visibility_pre,
        },
        "mention_chart": {
            "cur_series": mention_cur,
            "pre_series": mention_pre,
        },
        "average_rank_chart": {
            "cur_series": average_rank_cur,
            "pre_series": average_rank_pre,
        },
        "visibility_table": build_rank_table_rows(
            visibility_share,
            previous_rank.get("visibility_share") or {},
            **table_kwargs,
        ),
        "mention_table": build_rank_table_rows(
            mention_share,
            previous_rank.get("mention_rate") or {},
            **table_kwargs,
        ),
        "share_voice_table": build_rank_table_rows(
            share_voice,
            previous_rank.get("share_voice") or {},
            **table_kwargs,
        ),
        "average_rank_table": build_rank_table_rows(
            average_rank,
            previous_rank.get("average_rank") or {},
            **table_kwargs,
        ),
        "topic_visibility_ranks": topic_visibility_ranks,
    }
