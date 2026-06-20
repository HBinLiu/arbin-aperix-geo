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
from aperix_geo.services.analysis.aggregate import (
    daily_visibility_share_from_index,
    entity_metrics_rows_from_index,
    metrics_from_signals,
    rank_dict_from_entity_rows,
)
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import (
    AnalysisEntity,
    entity_chart_labels,
    list_analysis_entities,
    own_entity,
    resolve_analysis_entity,
)
from aperix_geo.services.analysis.performance import topics_performance_from_index
from aperix_geo.services.analysis.signal_index import build_dual_signal_window, window_has_data
from aperix_geo.services.analysis.signal_load import load_llm_response_signals
from aperix_geo.utils.sentiment import api_sentiment_label


def _metric_period(
    current: float | None,
    previous: float | None,
    *,
    has_previous: bool,
) -> dict[str, float | None]:
    return {
        "current": current,
        "previous": previous if has_previous else None,
    }


def _previous_value(value: float | None, *, has_previous: bool) -> float | None:
    return value if has_previous else None


def _label_rank(share: dict[str, float | None], label: str) -> int | None:
    if not share or label not in share:
        return None
    ranked = sorted(
        share.keys(),
        key=lambda key: share.get(key) if share.get(key) is not None else -1,
        reverse=True,
    )
    try:
        return ranked.index(label) + 1
    except ValueError:
        return None


def _metric_with_rank(
    current: float | None,
    previous: float | None,
    share: dict[str, float | None],
    rank_label: str,
) -> dict[str, float | int | None]:
    return {
        "current": current,
        "previous": previous,
        "rank": _label_rank(share, rank_label),
    }


def _build_rank_table_rows(
    current: dict[str, float | None],
    previous: dict[str, float | None] | None,
    *,
    entities: list[AnalysisEntity],
    has_previous: bool,
) -> list[dict[str, Any]]:
    prev = previous or {}
    display = {entity.label: entity.display_name for entity in entities}
    domains = {entity.label: entity.domain for entity in entities}
    rows: list[dict[str, Any]] = []
    for label in sorted(
        current.keys(),
        key=lambda key: current.get(key) if current.get(key) is not None else -1,
        reverse=True,
    ):
        pre_value: float | None = None
        if has_previous:
            raw = prev.get(label)
            pre_value = float(raw) if raw is not None else None
        rows.append(
            {
                "id": label,
                "label": display.get(label, label),
                "domain": domains.get(label, ""),
                "cur_value": current.get(label),
                "pre_value": pre_value,
            }
        )
    return rows


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
                "visibility": _metric_period(
                    row.get("visibility_rate"),
                    prev.get("visibility_rate"),
                    has_previous=has_previous,
                ),
                "citation": _metric_period(
                    row.get("citation_rate"),
                    prev.get("citation_rate"),
                    has_previous=has_previous,
                ),
                "sentiment": _metric_period(
                    row.get("sentiment_score"),
                    prev.get("sentiment_score"),
                    has_previous=has_previous,
                )
                | {"label": api_sentiment_label(row.get("sentiment_score"))},
                "average_rank": _metric_period(
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
    """概述页扁平化数据：KPI、可见度图表/排名表、主题表现。

    DB: 1× signals + 2× catalog (topics/prompts)。
    CPU: 单次遍历构建 current/previous 索引，复用于排名/KPI/图表/主题。
    """
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    own = own_entity(subject)

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    windows = build_dual_signal_window(
        all_signals,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )

    current_entity_rows = entity_metrics_rows_from_index(windows.current, subject=subject, entities=entities)
    previous_entity_rows = entity_metrics_rows_from_index(windows.previous, subject=subject, entities=entities)
    rank = rank_dict_from_entity_rows(current_entity_rows, own_label=own.label)
    previous_rank = rank_dict_from_entity_rows(previous_entity_rows, own_label=own.label)
    focus_label = entity.label

    has_previous = window_has_data(windows.previous)

    focus_current = windows.current.by_entity.get(entity.id, [])
    focus_previous = windows.previous.by_entity.get(entity.id, [])
    current_metrics = metrics_from_signals(
        focus_current,
        subject=subject,
        total_voice=windows.current.total_voice,
    )
    previous_metrics = metrics_from_signals(
        focus_previous,
        subject=subject,
        total_voice=windows.previous.total_voice,
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
        daily_visibility_share_from_index(windows.current, entities=entities, labels=series_labels),
        series_labels,
    )
    if has_previous:
        pre_series = align_previous_daily_to_current(
            cur_series,
            daily_visibility_share_from_index(windows.previous, entities=entities, labels=[focus_label]),
            [focus_label],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        )
    else:
        pre_series = [
            {"date": pt["date"], "values": {focus_label: None}} for pt in cur_series
        ]

    topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
    current_topics = topics_performance_from_index(
        windows.current,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        prompt_to_topic=prompt_to_topic,
    )
    previous_topics = topics_performance_from_index(
        windows.previous,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        prompt_to_topic=prompt_to_topic,
    )

    return {
        "entity_id": entity.id,
        "visibility": _metric_with_rank(
            current_metrics.visibility_rate,
            _previous_value(previous_metrics.visibility_rate, has_previous=has_previous),
            visibility_share,
            focus_label,
        ),
        "citation": _metric_with_rank(
            current_metrics.citation_rate,
            _previous_value(previous_metrics.citation_rate, has_previous=has_previous),
            citation_share,
            focus_label,
        ),
        "share_voice": _metric_with_rank(
            current_metrics.share_voice,
            _previous_value(previous_metrics.share_voice, has_previous=has_previous),
            share_voice,
            focus_label,
        ),
        "sentiment": {
            **_metric_with_rank(
                current_metrics.sentiment_score,
                _previous_value(previous_metrics.sentiment_score, has_previous=has_previous),
                sentiment_share,
                focus_label,
            ),
            "label": current_metrics.sentiment_label,
        },
        "visibility_chart": {
            "cur_series": cur_series,
            "pre_series": pre_series,
        },
        "visibility_table": _build_rank_table_rows(
            visibility_share,
            previous_rank.get("visibility_share") or {},
            entities=entities,
            has_previous=has_previous,
        ),
        "topic_table": _merge_topics(current_topics, previous_topics, has_previous=has_previous),
    }
