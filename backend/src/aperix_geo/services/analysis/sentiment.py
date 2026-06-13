"""Sentiment analysis aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.utils.text import reply_text
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import (
    aggregate_metrics,
    daily_sentiment_distribution_from_signals,
    metrics_from_signals,
)
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals
from aperix_geo.utils.sentiment import has_sentiment_score


def _platform_performance_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
    all_signals: list[LLMResponseSignalRow],
) -> list[dict[str, Any]]:
    aggregated = aggregate_metrics(
        signals,
        subject=subject,
        group_by="platform",
        entity_id=entity_id,
    )
    out: list[dict[str, Any]] = []
    for row in aggregated.rows:
        metrics = row["metrics"]
        out.append(
            {
                "platform": row["id"],
                "visibility_rate": metrics["visibility_rate"],
                "share_voice": metrics["share_voice"],
                "citation_rate": metrics["citation_rate"],
                "average_rank": metrics["average_rank"],
                "sentiment_score": metrics["sentiment_score"],
            }
        )
    _ = all_signals
    return sorted(out, key=lambda x: -(x["sentiment_score"] or -1))


def build_daily_sentiment_series(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    entity_signals = [row for row in all_signals if row.entity_id == entity.id]

    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in entity_signals:
        if row.mentioned and has_sentiment_score(row.sentiment_score):
            by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        scores = [float(row.sentiment_score) for row in by_date[day] if has_sentiment_score(row.sentiment_score)]
        series.append(
            {
                "date": day.isoformat(),
                "value": round(sum(scores) / len(scores), 1) if scores else None,
            }
        )

    return {"entity_id": entity.id, "own_label": entity.label, "series": series}


def build_sentiment_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """情感倾向页：分布趋势、平台排名、回复明细。"""
    entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    current_signals = [row for row in all_signals if dt_from <= row.created_at <= dt_to]
    prev_signals = [row for row in all_signals if prev_from <= row.created_at <= prev_to]
    entity_current = [row for row in current_signals if row.entity_id == entity.id]
    entity_prev = [row for row in prev_signals if row.entity_id == entity.id]

    metrics = metrics_from_signals(entity_current, subject=subject, all_signals_for_voice=current_signals)

    prompts = {
        p.id: p
        for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    response_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    signal_by_response = {row.response_id: row for row in entity_current if row.mentioned}

    responses: list[dict[str, Any]] = []
    for response in sorted(response_rows, key=lambda row: row.created_at, reverse=True):
        signal = signal_by_response.get(response.id)
        if not signal:
            continue
        prompt = prompts.get(response.prompt_id)
        responses.append(
            {
                "response_id": str(response.id),
                "platform": response.platform,
                "prompt_id": str(response.prompt_id),
                "prompt_text": prompt.text if prompt else "",
                "sentiment": signal.sentiment_label or "neutral",
                "sentiment_score": signal.sentiment_score,
                "sentiment_reason": (response.parsed or {}).get(
                    f"sentiment_reason_{'own' if entity.kind == 'own' else 'competitor'}"
                ),
                "reply_preview": reply_text(response.raw_text),
                "created_at": response.created_at.isoformat(),
            }
        )

    return {
        "entity_id": entity.id,
        "own_label": entity.label,
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
        "distribution_series": daily_sentiment_distribution_from_signals(
            current_signals,
            entity_id=entity.id,
        ),
        "platform_performance": _platform_performance_from_signals(
            current_signals,
            subject=subject,
            entity_id=entity.id,
            all_signals=current_signals,
        ),
        "previous_platform_performance": _platform_performance_from_signals(
            prev_signals,
            subject=subject,
            entity_id=entity.id,
            all_signals=prev_signals,
        ),
        "responses": responses,
    }
