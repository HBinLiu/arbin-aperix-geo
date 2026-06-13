"""Sentiment score helpers (0–100 point scale)."""

from __future__ import annotations

NO_SENTIMENT_SCORE = -1.0
NO_MENTION_RANK = 0

# 情感标签阈值（0–100）：中立 45~55（含边界）
_NEUTRAL_LOW = 45.0
_NEUTRAL_HIGH = 55.0


def has_sentiment_score(score: float) -> bool:
    return score >= 0.0


def has_mention_rank(rank: int) -> bool:
    return rank > 0


def persist_sentiment_score(score: float | None) -> float:
    if score is None:
        return NO_SENTIMENT_SCORE
    return float(score)


def persist_mention_rank(rank: int | None) -> int:
    if rank is None or rank <= 0:
        return 0
    return int(rank)


def api_mention_rank(rank: int | None) -> int | None:
    """Map stored rank to API null when unset."""
    if rank is None:
        return None
    value = int(rank)
    return value if has_mention_rank(value) else None


def api_sentiment_score(score: float | None) -> float | None:
    """Map stored score to API null when unset."""
    if score is None:
        return None
    value = float(score)
    return value if has_sentiment_score(value) else None


def clamp_sentiment_score(score: float) -> float:
    """Clamp ABSA / stored score to 0–100 points."""
    return round(max(0.0, min(100.0, float(score))), 1)


def sentiment_label_from_score(score: float) -> str:
    """Map 0–100 score to positive / neutral / negative."""
    value = float(score)
    if value > _NEUTRAL_HIGH:
        return "positive"
    if value < _NEUTRAL_LOW:
        return "negative"
    return "neutral"
