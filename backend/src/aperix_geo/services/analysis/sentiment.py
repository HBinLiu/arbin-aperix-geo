"""Sentiment analysis page — flattened payload."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis._page_helpers import build_rank_table_rows, previous_value
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.entity_sql import (
    query_dual_entity_window,
    query_sentiment_distribution,
    sentiment_distribution_from_signals,
)
from aperix_geo.services.analysis.metrics import MetricsBundle
from aperix_geo.services.sampling.platforms import resolve_platforms_for_sampling


def _sentiment_rank_table(
    current_entity_rows: list[dict[str, Any]],
    previous_entity_rows: list[dict[str, Any]],
    *,
    entities,
    has_previous: bool,
) -> list[dict[str, Any]]:
    current_scores = {
        row["label"]: row["metrics"].get("sentiment_score") for row in current_entity_rows
    }
    previous_scores = {
        row["label"]: row["metrics"].get("sentiment_score") for row in previous_entity_rows
    }
    labels_by_entity = {row["label"]: row["metrics"].get("sentiment_label") for row in current_entity_rows}
    rows = build_rank_table_rows(
        current_scores,
        previous_scores,
        entities=entities,
        has_previous=has_previous,
    )
    for row in rows:
        row["cur_label"] = labels_by_entity.get(row["id"])
    return rows


def _metrics_from_row(row: dict[str, Any] | None) -> MetricsBundle:
    if row is None:
        return MetricsBundle(0, None, None, None, None, None, None, None, None)
    metrics = row["metrics"]
    return MetricsBundle(
        response_count=int(metrics.get("response_count") or 0),
        visibility_rate=metrics.get("visibility_rate"),
        mention_rate=metrics.get("mention_rate"),
        share_voice=metrics.get("share_voice"),
        average_rank=metrics.get("average_rank"),
        citation_rate=metrics.get("citation_rate"),
        sentiment_score=metrics.get("sentiment_score"),
        sentiment_label=metrics.get("sentiment_label"),
        citation_coverage=metrics.get("citation_coverage"),
    )


def build_sentiment_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """情感倾向页扁平化数据：分布 / 品牌排名。"""
    focus_entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    platform_ids = resolve_platforms_for_sampling(subject, platform)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)

    windows = query_dual_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        entities=entities,
    )
    current = windows["current"]
    previous = windows["previous"]
    has_previous = previous.has_data

    focus_current_row = next((row for row in current.entity_rows if row["id"] == focus_entity.id), None)
    focus_previous_row = next((row for row in previous.entity_rows if row["id"] == focus_entity.id), None)
    current_metrics = _metrics_from_row(focus_current_row)
    previous_metrics = _metrics_from_row(focus_previous_row)

    distribution_series = query_sentiment_distribution(
        db,
        subject=subject,
        entity_id=focus_entity.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        platform_ids=platform_ids,
    )
    if not distribution_series:
        from aperix_geo.services.analysis.signal_load import load_llm_response_signals

        if load_llm_response_signals.override is not None:
            all_signals = load_llm_response_signals(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
            )
            distribution_series = sentiment_distribution_from_signals(
                all_signals,
                entity_id=focus_entity.id,
                platform_ids=platform_ids,
            )

    return {
        "entity_id": focus_entity.id,
        "sentiment_score": current_metrics.sentiment_score,
        "sentiment_label": current_metrics.sentiment_label,
        "sentiment_previous": previous_value(
            previous_metrics.sentiment_score,
            has_previous=has_previous,
        ),
        "distribution_series": distribution_series,
        "rank_table": _sentiment_rank_table(
            current.entity_rows,
            previous.entity_rows,
            entities=entities,
            has_previous=has_previous,
        ),
    }
