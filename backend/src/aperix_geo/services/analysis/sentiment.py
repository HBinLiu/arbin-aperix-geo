"""Sentiment analysis aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis._labels import own_label
from aperix_geo.services.analysis._parsed import avg_sentiment_points, mentions_own, parsed_sentiment_score, reply_text
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.metrics import compute_subject_metrics, platform_metrics_from_rows


def daily_sentiment_distribution(rows: list) -> list[dict[str, Any]]:
    """按日统计自有品牌提及回复的情感占比（正面 / 中立 / 负面）。"""
    by_date: dict[date, list] = defaultdict(list)
    for r in rows:
        if mentions_own(r.parsed or {}):
            by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for r in by_date[day]:
            label = (r.parsed or {}).get("sentiment_own") or "neutral"
            if label not in counts:
                label = "neutral"
            counts[label] += 1
        total = sum(counts.values()) or 1
        series.append(
            {
                "date": day.isoformat(),
                "positive": round(counts["positive"] / total, 4),
                "neutral": round(counts["neutral"] / total, 4),
                "negative": round(counts["negative"] / total, 4),
            }
        )
    return series


def build_daily_sentiment_series(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    by_date: dict[date, list] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        scores: list[float] = []
        for r in day_rows:
            score = parsed_sentiment_score(r.parsed or {})
            if score is not None:
                scores.append(score)
        series.append(
            {
                "date": day.isoformat(),
                "value": avg_sentiment_points(scores),
            }
        )

    return {"own_label": own_label(subject), "series": series}


def build_sentiment_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """情感倾向页：分布趋势、平台排名、回复明细。"""
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    all_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    current_rows = [r for r in all_rows if dt_from <= r.created_at <= dt_to]
    prev_rows = [r for r in all_rows if prev_from <= r.created_at <= prev_to]

    metrics = compute_subject_metrics(current_rows, subject=subject)
    by_platform_current: dict[str, list] = defaultdict(list)
    for r in current_rows:
        by_platform_current[r.platform].append(r)
    by_platform_prev: dict[str, list] = defaultdict(list)
    for r in prev_rows:
        by_platform_prev[r.platform].append(r)

    prompts = {
        p.id: p
        for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    responses: list[dict[str, Any]] = []
    for r in sorted(current_rows, key=lambda row: row.created_at, reverse=True):
        parsed = r.parsed or {}
        if not mentions_own(parsed):
            continue
        prompt = prompts.get(r.prompt_id)
        responses.append(
            {
                "response_id": str(r.id),
                "platform": r.platform,
                "prompt_id": str(r.prompt_id),
                "prompt_text": prompt.text if prompt else "",
                "sentiment": parsed.get("sentiment_own") or "neutral",
                "sentiment_score": parsed_sentiment_score(parsed),
                "sentiment_reason": parsed.get("sentiment_reason_own"),
                "reply_preview": reply_text(r.raw_text),
                "created_at": r.created_at.isoformat(),
            }
        )

    platform_performance = platform_metrics_from_rows(by_platform_current, subject=subject)
    platform_performance.sort(key=lambda row: -(row["sentiment_score"] or -1))

    return {
        "own_label": own_label(subject),
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
        "distribution_series": daily_sentiment_distribution(current_rows),
        "platform_performance": platform_performance,
        "previous_platform_performance": platform_metrics_from_rows(by_platform_prev, subject=subject),
        "responses": responses,
    }
