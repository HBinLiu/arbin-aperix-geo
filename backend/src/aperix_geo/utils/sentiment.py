"""Sentiment score helpers: 0 = unset / 未提及, 1–100 = valid ABSA score."""

from __future__ import annotations

# 情感标签阈值（1–100）：中立 45~70（含边界）；0 仅表示未评分
_NEUTRAL_LOW = 45.0
_NEUTRAL_HIGH = 70.0


def normalize_sentiment_score(score: float | None) -> float:
    """API / 读取：None、负数、旧哨兵 → 0；有效分保持 1–100。"""
    if score is None:
        return 0.0
    value = float(score)
    if value <= 0:
        return 0.0
    return min(100.0, value)


def is_scored_sentiment(score: float | None) -> bool:
    """是否参与情感聚合（0 视为未提及 / 未评分）。"""
    return normalize_sentiment_score(score) > 0


def persist_sentiment_score(score: float | None) -> float:
    if score is None:
        return 0.0
    value = float(score)
    if value <= 0:
        return 0.0
    return clamp_sentiment_score(value)


def persist_sentiment_reason(reason: str | None) -> str:
    return (reason or "").strip()


def api_sentiment_score(score: float | None) -> float:
    return normalize_sentiment_score(score)


def api_sentiment_label(score: float | None) -> str:
    value = normalize_sentiment_score(score)
    if value <= 0:
        return "negative"
    return sentiment_label_from_score(value)


def clamp_sentiment_score(score: float) -> float:
    """Clamp ABSA output to 1–100 points."""
    return round(max(1.0, min(100.0, float(score))), 1)


def sentiment_label_from_score(score: float) -> str:
    """Map 1–100 score to positive / neutral / negative."""
    value = float(score)
    if value > _NEUTRAL_HIGH:
        return "positive"
    if value < _NEUTRAL_LOW:
        return "negative"
    return "neutral"
