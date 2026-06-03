"""Tests for datetime helpers."""

from datetime import UTC

from aperix_geo.utils.datetime import parse_iso_datetime


def test_parse_iso_datetime_z_suffix() -> None:
    dt = parse_iso_datetime("2024-01-15T08:00:00Z")
    assert dt.tzinfo == UTC


def test_parse_iso_datetime_naive_gets_utc() -> None:
    dt = parse_iso_datetime("2024-01-15T08:00:00")
    assert dt.tzinfo == UTC
