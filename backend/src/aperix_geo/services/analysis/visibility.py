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
from aperix_geo.services.analysis.aggregate import (
    daily_average_rank_series_from_index,
    daily_share_series_from_index,
    entity_metrics_rows_from_index,
    group_signals_by_topic,
    metrics_from_signals,
    rank_dict_from_entity_rows,
    top_entity_labels_by_visibility,
)
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.dashboard import (
    _build_rank_table_rows,
    _metric_with_rank,
    _previous_value,
)
from aperix_geo.services.analysis.entity import (
    entity_chart_labels,
    list_analysis_entities,
    own_entity,
    resolve_analysis_entity,
)
from aperix_geo.services.analysis.signal_index import (
    SignalWindowIndex,
    build_dual_signal_window,
    window_has_data,
)
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals


def _signals_from_index(index: SignalWindowIndex) -> list[LLMResponseSignalRow]:
    return [row for rows in index.by_date.values() for row in rows]


def build_topic_visibility_ranks(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    window: SignalWindowIndex | None = None,
    topics: dict[UUID, Topic] | list[Topic] | None = None,
    prompt_to_topic: dict[UUID, UUID] | None = None,
) -> list[dict[str, Any]]:
    """各主题下按可见度排序的品牌 Top5（用于主题可见度排名表）。"""
    if window is None:
        all_signals = load_llm_response_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
        )
        from aperix_geo.services.analysis.signal_index import index_signals

        window = index_signals(all_signals)

    if topics is None or prompt_to_topic is None:
        topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)

    by_topic = group_signals_by_topic(_signals_from_index(window), prompt_to_topic=prompt_to_topic)

    topic_rows = topics.values() if isinstance(topics, dict) else topics
    out: list[dict[str, Any]] = []
    for topic in sorted(topic_rows, key=lambda item: item.name):
        out.append(
            {
                "topic_id": str(topic.id),
                "topic_name": topic.name,
                "ranks": top_entity_labels_by_visibility(
                    by_topic.get(topic.id, []),
                    subject=subject,
                    limit=TOPIC_VISIBILITY_RANK_LIMIT,
                ),
            }
        )
    return out


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
    """可见度页扁平化数据：四指标 KPI / 图表 / 排名表 + 主题可见度。

    DB: 1× signals + 1× catalog (topics/prompts)。
    CPU: 双窗口索引一次构建，复用于排名、日序列与主题榜。
    """
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    own = own_entity(subject)
    focus_label = entity.label

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    windows = build_dual_signal_window(
        all_signals,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )

    current_entity_rows = entity_metrics_rows_from_index(
        windows.current, subject=subject, entities=entities
    )
    previous_entity_rows = entity_metrics_rows_from_index(
        windows.previous, subject=subject, entities=entities
    )
    rank = rank_dict_from_entity_rows(current_entity_rows, own_label=own.label)
    previous_rank = rank_dict_from_entity_rows(previous_entity_rows, own_label=own.label)
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
    mention_share = rank.get("mention_rate") or {}
    share_voice = rank.get("share_voice") or {}
    average_rank = rank.get("average_rank") or {}

    visibility_cur = slim_daily_series(
        daily_share_series_from_index(
            windows.current,
            entities=entities,
            metric="visibility",
            labels=series_labels,
        ),
        series_labels,
    )
    mention_cur = slim_daily_series(
        daily_share_series_from_index(
            windows.current,
            entities=entities,
            metric="mention",
            labels=series_labels,
        ),
        series_labels,
    )
    average_rank_cur = daily_average_rank_series_from_index(
        windows.current,
        entity_id=entity.id,
    )

    if has_previous:
        visibility_pre = align_previous_daily_to_current(
            visibility_cur,
            daily_share_series_from_index(
                windows.previous,
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
            daily_share_series_from_index(
                windows.previous,
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
            daily_average_rank_series_from_index(windows.previous, entity_id=entity.id),
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        )
    else:
        visibility_pre = [
            {"date": pt["date"], "values": {focus_label: None}} for pt in visibility_cur
        ]
        mention_pre = [{"date": pt["date"], "values": {focus_label: None}} for pt in mention_cur]
        average_rank_pre = [
            {"date": pt["date"], "value": None} for pt in average_rank_cur
        ]

    topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
    topic_visibility_ranks = build_topic_visibility_ranks(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        window=windows.current,
        topics=topics,
        prompt_to_topic=prompt_to_topic,
    )

    table_kwargs = {
        "entities": entities,
        "has_previous": has_previous,
    }

    return {
        "entity_id": entity.id,
        "visibility": _metric_with_rank(
            current_metrics.visibility_rate,
            _previous_value(previous_metrics.visibility_rate, has_previous=has_previous),
            visibility_share,
            focus_label,
        ),
        "mention": _metric_with_rank(
            current_metrics.mention_rate,
            _previous_value(previous_metrics.mention_rate, has_previous=has_previous),
            mention_share,
            focus_label,
        ),
        "share_voice": _metric_with_rank(
            current_metrics.share_voice,
            _previous_value(previous_metrics.share_voice, has_previous=has_previous),
            share_voice,
            focus_label,
        ),
        "average_rank": _metric_with_rank(
            current_metrics.average_rank,
            _previous_value(previous_metrics.average_rank, has_previous=has_previous),
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
        "visibility_table": _build_rank_table_rows(
            visibility_share,
            previous_rank.get("visibility_share") or {},
            **table_kwargs,
        ),
        "mention_table": _build_rank_table_rows(
            mention_share,
            previous_rank.get("mention_rate") or {},
            **table_kwargs,
        ),
        "share_voice_table": _build_rank_table_rows(
            share_voice,
            previous_rank.get("share_voice") or {},
            **table_kwargs,
        ),
        "average_rank_table": _build_rank_table_rows(
            average_rank,
            previous_rank.get("average_rank") or {},
            **table_kwargs,
        ),
        "topic_visibility_ranks": topic_visibility_ranks,
    }
