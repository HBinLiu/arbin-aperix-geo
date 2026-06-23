"""Signal-path helpers for platform analysis regression tests."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.aggregate import (
    aggregate_metrics,
    daily_platform_metric_series_from_signals,
    group_signals_by_topic,
    metrics_from_signals,
)
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow

PLATFORM_CHART_METRICS = ("visibility", "share_voice", "citation", "average_rank", "sentiment")
METRIC_FIELDS = {
    "visibility": "visibility_rate",
    "share_voice": "share_voice",
    "citation": "citation_rate",
    "average_rank": "average_rank",
    "sentiment": "sentiment_score",
}


def platform_performance_rows(
    all_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
) -> list[dict[str, Any]]:
    by_platform_all: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    by_platform_entity: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in all_signals:
        by_platform_all[row.platform].append(row)
        if row.entity_id == entity_id:
            by_platform_entity[row.platform].append(row)

    out: list[dict[str, Any]] = []
    for platform_id, subset in by_platform_entity.items():
        metrics = metrics_from_signals(
            subset,
            subject=subject,
            all_signals_for_voice=by_platform_all.get(platform_id, []),
        )
        out.append(
            {
                "platform": platform_id,
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "share_voice": metrics.share_voice,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "sentiment_label": metrics.sentiment_label,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


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


def build_matrix_cells(
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


def build_platform_charts(
    platform_ids: list[str],
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    by_platform: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        by_platform[row.platform].append(row)

    charts: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for metric in PLATFORM_CHART_METRICS:
        field = METRIC_FIELDS[metric]
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
