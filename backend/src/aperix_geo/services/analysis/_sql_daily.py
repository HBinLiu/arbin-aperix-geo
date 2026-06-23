"""Shared helpers for daily SQL row → chart series conversion."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date
from typing import Any

from aperix_geo.services.analysis.entity import AnalysisEntity


def parse_row_day(day: date | str) -> date:
    if isinstance(day, str):
        return date.fromisoformat(day)
    return day


def citation_rate(with_link: int, mentioned: int) -> float:
    return round(with_link / mentioned, 4) if mentioned else 0.0


def format_multi_label_daily_series(
    by_day: dict[date, dict[str, float]],
) -> list[dict[str, Any]]:
    return [{"date": day.isoformat(), "values": values} for day, values in sorted(by_day.items())]


def daily_multi_label_series(
    rows: list[Any],
    *,
    entities: list[AnalysisEntity],
    value_fn: Callable[[Any], float],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    label_by_id = {entity.id: entity.label for entity in entities}
    label_set = set(labels) if labels is not None else None
    by_day: dict[date, dict[str, float]] = defaultdict(dict)

    for row in rows:
        day = parse_row_day(row.day)
        entity_id = str(row.entity_id)
        label = label_by_id.get(entity_id)
        if not label or (label_set is not None and label not in label_set):
            continue
        by_day[day][label] = value_fn(row)

    return format_multi_label_daily_series(by_day)


def daily_citation_series(
    rows: list[Any],
    *,
    entities: list[AnalysisEntity],
    labels: list[str] | None = None,
    with_link_attr: str = "with_link",
    mentioned_attr: str = "mentioned",
) -> list[dict[str, Any]]:
    def value_fn(row: Any) -> float:
        with_link = int(getattr(row, with_link_attr, 0) or 0)
        mentioned = int(getattr(row, mentioned_attr, 0) or 0)
        return citation_rate(with_link, mentioned)

    return daily_multi_label_series(
        rows,
        entities=entities,
        value_fn=value_fn,
        labels=labels,
    )
