"""Time-series alignment helpers for period-over-period charts."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

VISIBILITY_CHART_LABEL_LIMIT = 5
TOPIC_VISIBILITY_RANK_LIMIT = 5


def previous_date_range(dt_from: datetime, dt_to: datetime) -> tuple[datetime, datetime]:
    span = dt_to - dt_from
    prev_to = dt_from - timedelta(milliseconds=1)
    prev_from = prev_to - span
    return prev_from, prev_to


def top_visibility_labels(
    visibility_share: dict[str, float],
    own: str,
    limit: int | None = VISIBILITY_CHART_LABEL_LIMIT,
) -> list[str]:
    ranked = sorted(visibility_share.keys(), key=lambda k: visibility_share.get(k, 0), reverse=True)
    if limit is None:
        return ranked
    top = ranked[:limit]
    if own and own not in top and own in visibility_share:
        top = ranked[: limit - 1] + [own]
    return top


def slim_daily_series(
    series: list[dict[str, Any]],
    label_keys: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "date": pt["date"],
            "values": {k: pt["values"].get(k, 0) for k in label_keys},
        }
        for pt in series
    ]


def align_previous_single_series(
    current_series: list[dict[str, Any]],
    previous_series: list[dict[str, Any]],
    *,
    current_start: date,
    previous_start: date,
) -> list[dict[str, Any]]:
    prev_by_offset: dict[int, dict[str, Any]] = {}
    for pt in previous_series:
        day = date.fromisoformat(pt["date"])
        prev_by_offset[(day - previous_start).days] = pt

    aligned: list[dict[str, Any]] = []
    for pt in current_series:
        day = date.fromisoformat(pt["date"])
        offset = (day - current_start).days
        prev_pt = prev_by_offset.get(offset)
        aligned.append(
            {
                "date": pt["date"],
                "value": prev_pt.get("value") if prev_pt else None,
            }
        )
    return aligned


def align_previous_daily_to_current(
    current_series: list[dict[str, Any]],
    previous_series: list[dict[str, Any]],
    labels: list[str],
    *,
    current_start: date,
    previous_start: date,
) -> list[dict[str, Any]]:
    prev_by_offset: dict[int, dict[str, Any]] = {}
    for pt in previous_series:
        day = date.fromisoformat(pt["date"])
        prev_by_offset[(day - previous_start).days] = pt

    aligned: list[dict[str, Any]] = []
    for pt in current_series:
        day = date.fromisoformat(pt["date"])
        offset = (day - current_start).days
        prev_pt = prev_by_offset.get(offset)
        values = {lab: (prev_pt["values"].get(lab, 0) if prev_pt else 0) for lab in labels}
        aligned.append(
            {
                "date": pt["date"],
                "values": values,
            }
        )
    return aligned
