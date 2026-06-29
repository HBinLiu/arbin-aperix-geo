"""Parse plan/subject sampling frequency codes."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_SAMPLING_FREQUENCIES: frozenset[str] = frozenset({"daily_1", "daily_3", "daily_7"})


@dataclass(frozen=True, slots=True)
class SamplingInterval:
    days: int


def normalize_sampling_frequency(frequency: str) -> str:
    return (frequency or "daily_1").strip().lower()


def sampling_interval_days(frequency: str) -> int:
    """Return minimum whole-day interval between scheduled samples."""
    value = normalize_sampling_frequency(frequency)
    if not value:
        return 1
    if value.startswith("daily_"):
        try:
            count = int(value.split("_", 1)[1])
        except (IndexError, ValueError):
            return 1
        return max(1, count)
    return 1
