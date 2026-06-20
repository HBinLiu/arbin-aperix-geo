"""Platform analysis page — flattened payload (single signal load)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import (
    aggregate_metrics,
    daily_platform_metric_series_from_signals,
    group_signals_by_topic,
    metrics_from_signals,
)
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.performance import platform_performance_rows
from aperix_geo.services.analysis.signal_index import SignalWindowIndex, build_dual_signal_window
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals
from aperix_geo.services.sampling.platforms import resolve_platforms_for_sampling

_PLATFORM_METRICS = ("visibility", "share_voice", "citation", "average_rank", "sentiment")
_METRIC_FIELDS = {
    "visibility": "visibility_rate",
    "share_voice": "share_voice",
    "citation": "citation_rate",
    "average_rank": "average_rank",
    "sentiment": "sentiment_score",
}


def _signals_flat(index: SignalWindowIndex) -> list[LLMResponseSignalRow]:
    return [row for rows in index.by_date.values() for row in rows]


def _matrix_cell(
    row_id: str,
    platform_id: str,
    *,
    visibility_rate: float | None,
    share_voice: float | None,
    citation_rate: float | None,
    average_rank: float | None,
    sentiment_score: float | None,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "platform_id": platform_id,
        "visibility_rate": visibility_rate,
        "share_voice": share_voice,
        "citation_rate": citation_rate,
        "average_rank": average_rank,
        "sentiment_score": sentiment_score,
    }


def _build_matrix_cells(
    signals: list[LLMResponseSignalRow],
    *,
    row_dimension: str,
    platform_ids: list[str],
    subject: Subject,
    entities,
    focus_entity,
    prompt_to_topic: dict,
) -> list[dict[str, Any]]:
    by_platform: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        by_platform[row.platform].append(row)

    cells: list[dict[str, Any]] = []

    for platform_key in platform_ids:
        platform_signals = by_platform.get(platform_key, [])

        if row_dimension == "competitor":
            entity_agg = aggregate_metrics(platform_signals, subject=subject, group_by="entity")
            entity_metrics = {row["label"]: row["metrics"] for row in entity_agg.rows}

            for entity in entities:
                metrics = entity_metrics.get(entity.label, {})
                cells.append(
                    _matrix_cell(
                        entity.id,
                        platform_key,
                        visibility_rate=metrics.get("visibility_rate"),
                        share_voice=metrics.get("share_voice"),
                        citation_rate=metrics.get("citation_rate"),
                        average_rank=metrics.get("average_rank"),
                        sentiment_score=metrics.get("sentiment_score"),
                    )
                )
            continue

        topic_entity_signals = [row for row in platform_signals if row.entity_id == focus_entity.id]
        by_topic = group_signals_by_topic(topic_entity_signals, prompt_to_topic=prompt_to_topic)
        for tid, subset in by_topic.items():
            metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=platform_signals)
            cells.append(
                _matrix_cell(
                    str(tid),
                    platform_key,
                    visibility_rate=metrics.visibility_rate,
                    share_voice=metrics.share_voice,
                    citation_rate=metrics.citation_rate,
                    average_rank=metrics.average_rank,
                    sentiment_score=metrics.sentiment_score,
                )
            )

    return cells


def _build_platform_charts(
    platform_ids: list[str],
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Per-metric multi-platform daily series keyed by platform id."""
    by_platform: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        by_platform[row.platform].append(row)

    charts: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for metric in _PLATFORM_METRICS:
        field = _METRIC_FIELDS[metric]
        per_platform: dict[str, list[dict[str, Any]]] = {
            platform_key: daily_platform_metric_series_from_signals(
                by_platform.get(platform_key, []),
                subject=subject,
                entity_id=entity_id,
                field=field,
            )
            for platform_key in platform_ids
        }

        dates = sorted({point["date"] for points in per_platform.values() for point in points})
        current: list[dict[str, Any]] = []
        for date in dates:
            values: dict[str, float] = {}
            for platform_key in platform_ids:
                for point in per_platform[platform_key]:
                    if point["date"] == date and point.get("value") is not None:
                        values[platform_key] = float(point["value"])
                        break
            current.append({"date": date, "values": values})

        charts[metric] = {"current": current}

    return charts


def build_platform_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
    matrix_row: str = "competitor",
) -> dict[str, Any]:
    """平台页扁平化数据：矩阵单元 / 平台排名 / 分指标多平台趋势。"""
    focus_entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    platform_ids = resolve_platforms_for_sampling(subject, platform)

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
    current_signals = _signals_flat(windows.current)
    previous_signals = _signals_flat(windows.previous)

    entities = list_analysis_entities(subject)
    prompt_to_topic: dict = {}
    if matrix_row == "topic":
        _topics, _prompts, prompt_to_topic = load_topic_prompt_catalog(db, subject.id)

    matrix_kwargs = {
        "row_dimension": matrix_row,
        "platform_ids": platform_ids,
        "subject": subject,
        "entities": entities,
        "focus_entity": focus_entity,
        "prompt_to_topic": prompt_to_topic,
    }
    matrix_cells = _build_matrix_cells(current_signals, **matrix_kwargs)
    matrix_cells_previous = _build_matrix_cells(previous_signals, **matrix_kwargs)

    return {
        "entity_id": focus_entity.id,
        "matrix_row": matrix_row,
        "matrix_cells": {
            "current": matrix_cells,
            "previous": matrix_cells_previous,
        },
        "performance": {
            "current": platform_performance_rows(
                current_signals,
                subject=subject,
                entity_id=focus_entity.id,
            ),
            "previous": platform_performance_rows(
                previous_signals,
                subject=subject,
                entity_id=focus_entity.id,
            ),
        },
        "charts": _build_platform_charts(
            platform_ids,
            current_signals,
            subject=subject,
            entity_id=focus_entity.id,
        ),
    }
