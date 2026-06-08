"""Sentiment score helpers (0–100 point scale)."""

from __future__ import annotations


def sentiment_points(score: float | None) -> float | None:
    """Normalize a stored sentiment value to 0–100 (supports legacy 0–1)."""
    if score is None:
        return None
    value = float(score)
    if value <= 1.0:
        value *= 100.0
    return round(max(0.0, min(100.0, value)), 1)


def absa_score_to_points(score: float | None) -> float | None:
    """Map ABSA score (-1~1) to 0–100 points."""
    if score is None:
        return None
    value = (float(score) + 1.0) / 2.0 * 100.0
    return round(max(0.0, min(100.0, value)), 1)


def absa_score_to_label(score: float | None) -> str:
    """Map ABSA score (-1~1) to positive / neutral / negative."""
    if score is None:
        return "neutral"
    value = float(score)
    if value > 0.15:
        return "positive"
    if value < -0.15:
        return "negative"
    return "neutral"
