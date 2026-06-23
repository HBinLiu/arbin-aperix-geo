"""Console overview page — single aggregated payload."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import (
    align_previous_daily_to_current,
    previous_date_range,
    slim_daily_series,
)
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis._page_helpers import (
    build_rank_table_rows,
    metric_period,
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
    daily_share_series_for_window,
    query_dual_entity_window,
)
from aperix_geo.services.analysis.grouped_sql import query_topic_metrics
from aperix_geo.services.analysis.aggregate import rank_dict_from_entity_rows
from aperix_geo.utils.sentiment import api_sentiment_label


def _metrics_from_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {}
    return row["metrics"]


def _merge_topics(
    current_topics: list[dict[str, Any]],
    previous_topics: list[dict[str, Any]],
    *,
    has_previous: bool,
) -> list[dict[str, Any]]:
    prev_map = {row["topic_id"]: row for row in previous_topics}
    merged: list[dict[str, Any]] = []
    for row in current_topics:
        prev = prev_map.get(row["topic_id"], {})
        merged.append(
            {
                "topic_id": row["topic_id"],
                "topic_name": row["topic_name"],
                "response_count": row.get("response_count") or 0,
                "visibility": metric_period(
                    row.get("visibility_rate"),
                    prev.get("visibility_rate"),
                    has_previous=has_previous,
                ),
                "citation": metric_period(
                    row.get("citation_rate"),
                    prev.get("citation_rate"),
                    has_previous=has_previous,
                ),
                "sentiment": metric_period(
                    row.get("sentiment_score"),
                    prev.get("sentiment_score"),
                    has_previous=has_previous,
                )
                | {"label": api_sentiment_label(row.get("sentiment_score"))},
                "average_rank": metric_period(
                    row.get("average_rank"),
                    prev.get("average_rank"),
                    has_previous=has_previous,
                ),
            }
        )
    merged.sort(key=lambda item: item["visibility"]["current"] or 0, reverse=True)
    return merged


def build_dashboard_overview(
    db: Session,
    *,
    subject: Subject,
    entity_id: str | None = None,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    dt_from: datetime,
    dt_to: datetime,
) -> dict[str, Any]:
    """概述页扁平化数据：KPI、可见度图表/排名表、主题表现。"""
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
        entities=entities,
    )
    current = windows["current"]
    previous = windows["previous"]
    has_previous = previous.has_data

    current_entity_rows = current.entity_rows
    previous_entity_rows = previous.entity_rows
    rank = rank_dict_from_entity_rows(current_entity_rows, own_label=own.label)
    previous_rank = rank_dict_from_entity_rows(previous_entity_rows, own_label=own.label)

    focus_current = _metrics_from_row(
        next((row for row in current_entity_rows if row["id"] == entity.id), None)
    )
    focus_previous = _metrics_from_row(
        next((row for row in previous_entity_rows if row["id"] == entity.id), None)
    )

    series_labels = entity_chart_labels(entities)
    visibility_share = rank.get("visibility_share") or {}
    citation_share = rank.get("citation_share") or {}
    share_voice = rank.get("share_voice") or {}
    sentiment_share = {
        label: value
        for label, value in (rank.get("sentiment_score") or {}).items()
        if value is not None
    }

    cur_series = slim_daily_series(
        daily_share_series_for_window(
            current,
            entities=entities,
            metric="visibility",
            labels=series_labels,
        ),
        series_labels,
    )
    if has_previous:
        pre_series = align_previous_daily_to_current(
            cur_series,
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
    else:
        pre_series = [
            {"date": pt["date"], "values": {focus_label: None}} for pt in cur_series
        ]

    topics, _prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
    current_topics = query_topic_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    previous_topics = query_topic_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        dt_from=prev_from,
        dt_to=prev_to,
        platform=platform,
        topic_id=topic_id,
    )

    return {
        "entity_id": entity.id,
        "visibility": metric_with_rank(
            focus_current.get("visibility_rate"),
            previous_value(focus_previous.get("visibility_rate"), has_previous=has_previous),
            visibility_share,
            focus_label,
        ),
        "citation": metric_with_rank(
            focus_current.get("citation_rate"),
            previous_value(focus_previous.get("citation_rate"), has_previous=has_previous),
            citation_share,
            focus_label,
        ),
        "share_voice": metric_with_rank(
            focus_current.get("share_voice"),
            previous_value(focus_previous.get("share_voice"), has_previous=has_previous),
            share_voice,
            focus_label,
        ),
        "sentiment": {
            **metric_with_rank(
                focus_current.get("sentiment_score"),
                previous_value(focus_previous.get("sentiment_score"), has_previous=has_previous),
                sentiment_share,
                focus_label,
            ),
            "label": focus_current.get("sentiment_label"),
        },
        "visibility_chart": {
            "cur_series": cur_series,
            "pre_series": pre_series,
        },
        "visibility_table": build_rank_table_rows(
            visibility_share,
            previous_rank.get("visibility_share") or {},
            entities=entities,
            has_previous=has_previous,
        ),
        "topic_table": _merge_topics(current_topics, previous_topics, has_previous=has_previous),
    }
