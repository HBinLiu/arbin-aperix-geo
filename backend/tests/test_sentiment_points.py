"""Tests for sentiment point scale helpers."""

from aperix_geo.utils.sentiment import sentiment_points


def test_sentiment_points_from_fraction() -> None:
    assert sentiment_points(0.85) == 85.0
    assert sentiment_points(1.0) == 100.0


def test_sentiment_points_from_hundred_scale() -> None:
    assert sentiment_points(72.5) == 72.5
    assert sentiment_points(100) == 100.0
