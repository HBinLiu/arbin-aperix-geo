"""Sentiment analysis page — flattened payload (single signal load)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import (
    daily_sentiment_distribution_from_signals,
    entity_metrics_rows_from_index,
    metrics_from_signals,
)
from aperix_geo.services.analysis.dashboard import _build_rank_table_rows, _previous_value
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.signal_index import build_dual_signal_window, window_has_data
from aperix_geo.services.analysis.signal_load import load_llm_response_signals
from aperix_geo.services.sampling.platforms import resolve_platforms_for_sampling


def _sentiment_rank_table(
    current_entity_rows: list[dict[str, Any]],
    previous_entity_rows: list[dict[str, Any]],
    *,
    entities,
    has_previous: bool,
) -> list[dict[str, Any]]:
    current_scores = {
        row["label"]: row["metrics"].get("sentiment_score") for row in current_entity_rows
    }
    previous_scores = {
        row["label"]: row["metrics"].get("sentiment_score") for row in previous_entity_rows
    }
    labels_by_entity = {row["label"]: row["metrics"].get("sentiment_label") for row in current_entity_rows}
    rows = _build_rank_table_rows(
        current_scores,
        previous_scores,
        entities=entities,
        has_previous=has_previous,
    )
    for row in rows:
        row["cur_label"] = labels_by_entity.get(row["id"])
    return rows


def build_sentiment_analysis(
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
    """情感倾向页扁平化数据：分布 / 品牌排名。

    DB: 1× signals（含上一周期窗口）。
    """
    focus_entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    platform_ids = resolve_platforms_for_sampling(subject, platform)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)

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
    has_previous = window_has_data(windows.previous)

    current_entity_rows = entity_metrics_rows_from_index(
        windows.current, subject=subject, entities=entities
    )
    previous_entity_rows = entity_metrics_rows_from_index(
        windows.previous, subject=subject, entities=entities
    )

    focus_current = windows.current.by_entity.get(focus_entity.id, [])
    focus_previous = windows.previous.by_entity.get(focus_entity.id, [])
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

    return {
        "entity_id": focus_entity.id,
        "sentiment_score": current_metrics.sentiment_score,
        "sentiment_label": current_metrics.sentiment_label,
        "sentiment_previous": _previous_value(
            previous_metrics.sentiment_score,
            has_previous=has_previous,
        ),
        "distribution_series": daily_sentiment_distribution_from_signals(
            [row for rows in windows.current.by_date.values() for row in rows],
            entity_id=focus_entity.id,
            platform_ids=platform_ids,
        ),
        "rank_table": _sentiment_rank_table(
            current_entity_rows,
            previous_entity_rows,
            entities=entities,
            has_previous=has_previous,
        ),
    }
