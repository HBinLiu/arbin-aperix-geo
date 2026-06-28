"""Parse plan/subject sampling frequency codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SamplingInterval:
    days: int


def sampling_interval_days(frequency: str) -> int:
    """Return minimum whole-day interval between scheduled samples."""
    value = (frequency or "daily_1").strip().lower()
    if not value:
        return 1
    if value.startswith("daily_"):
        try:
            count = int(value.split("_", 1)[1])
        except (IndexError, ValueError):
            return 1
        return max(1, count)
    if value.startswith("weekly_"):
        try:
            count = int(value.split("_", 1)[1])
        except (IndexError, ValueError):
            return 7
        return max(7, 7 * count)
    return 1
