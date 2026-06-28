"""Tests for sampling frequency parsing."""

from aperix_geo.services.sampling.frequency import sampling_interval_days


def test_sampling_interval_days_daily() -> None:
    assert sampling_interval_days("daily_1") == 1
    assert sampling_interval_days("daily_3") == 3


def test_sampling_interval_days_weekly() -> None:
    assert sampling_interval_days("weekly_1") == 7


def test_sampling_interval_days_fallback() -> None:
    assert sampling_interval_days("") == 1
    assert sampling_interval_days("unknown") == 1
