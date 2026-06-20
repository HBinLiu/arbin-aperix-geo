"""In-memory indexes for analysis windows — single-pass grouping."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow


@dataclass(frozen=True)
class SignalWindowIndex:
    """Pre-grouped signal rows for one time window."""

    by_entity: dict[str, list[LLMResponseSignalRow]]
    by_brand: dict[UUID, list[LLMResponseSignalRow]]
    by_date: dict[date, list[LLMResponseSignalRow]]
    by_date_entity: dict[date, dict[str, list[LLMResponseSignalRow]]]
    total_voice: int


@dataclass(frozen=True)
class DualSignalWindow:
    current: SignalWindowIndex
    previous: SignalWindowIndex


def index_signals(signals: list[LLMResponseSignalRow]) -> SignalWindowIndex:
    by_entity: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    by_brand: dict[UUID, list[LLMResponseSignalRow]] = defaultdict(list)
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    by_date_entity: dict[date, dict[str, list[LLMResponseSignalRow]]] = defaultdict(
        lambda: defaultdict(list)
    )
    total_voice = 0
    for row in signals:
        by_entity[row.entity_id].append(row)
        by_brand[row.brand_id].append(row)
        day = row.created_at.date()
        by_date[day].append(row)
        by_date_entity[day][row.entity_id].append(row)
        total_voice += row.mention_count
    return SignalWindowIndex(
        by_entity=dict(by_entity),
        by_brand=dict(by_brand),
        by_date=dict(by_date),
        by_date_entity={day: dict(entities) for day, entities in by_date_entity.items()},
        total_voice=total_voice,
    )


def window_has_data(index: SignalWindowIndex) -> bool:
    """Whether the window contains any signal rows (distinct sampling responses)."""
    return bool(index.by_date)


def build_dual_signal_window(
    all_signals: list[LLMResponseSignalRow],
    *,
    dt_from: datetime,
    dt_to: datetime,
    prev_from: datetime,
    prev_to: datetime,
) -> DualSignalWindow:
    """Split combined signals into current/previous windows and index each once."""
    current: list[LLMResponseSignalRow] = []
    previous: list[LLMResponseSignalRow] = []
    for row in all_signals:
        if dt_from <= row.created_at <= dt_to:
            current.append(row)
        elif prev_from <= row.created_at <= prev_to:
            previous.append(row)
    return DualSignalWindow(
        current=index_signals(current),
        previous=index_signals(previous),
    )
