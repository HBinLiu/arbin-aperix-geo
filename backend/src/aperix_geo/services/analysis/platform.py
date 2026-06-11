"""Platform matrix analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import (
    aggregate_metrics,
    citation_share_from_signals,
    daily_platform_metric_series_from_signals,
    group_signals_by_topic,
    metrics_from_signals,
)
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.performance import build_platform_performance
from aperix_geo.services.analysis.signal_load import load_llm_response_signals

PLATFORM_MATRIX_METRICS = ("visibility", "share_voice", "citation", "average_rank", "sentiment")

_METRIC_FIELDS = {
    "visibility": "visibility_rate",
    "share_voice": "share_voice",
    "citation": "citation_rate",
    "average_rank": "average_rank",
    "sentiment": "sentiment_score",
}


def build_platform_matrix_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """平台矩阵：竞争对手/主题 × 平台 × 指标，含平台排名与分平台趋势。"""
    topic_entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    current_signals = [row for row in all_signals if dt_from <= row.created_at <= dt_to]

    entities = list_analysis_entities(subject)
    own = next(entity for entity in entities if entity.kind == "own")
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
    }
    prompt_to_topic = {pid: p.topic_id for pid, p in prompts.items()}

    by_platform_current: dict[str, list] = defaultdict(list)
    for row in current_signals:
        by_platform_current[row.platform].append(row)

    platform_list = sorted(by_platform_current.keys())
    competitor_rows = [{"id": entity.id, "label": entity.label, "is_own": entity.kind == "own"} for entity in entities]
    topic_rows = [{"id": str(tid), "label": topics[tid].name} for tid in sorted(topics.keys(), key=lambda k: topics[k].name)]

    competitor_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {entity.label: {} for entity in entities} for metric in PLATFORM_MATRIX_METRICS
    }
    topic_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {str(tid): {} for tid in topics} for metric in PLATFORM_MATRIX_METRICS
    }

    for platform, platform_signals in by_platform_current.items():
        entity_agg = aggregate_metrics(platform_signals, subject=subject, group_by="entity")
        _, citation_share, _ = citation_share_from_signals(platform_signals, subject=subject)
        entity_metrics = {row["label"]: row["metrics"] for row in entity_agg.rows}

        for entity in entities:
            metrics = entity_metrics.get(entity.label, {})
            competitor_values["visibility"][entity.label][platform] = metrics.get("visibility_rate")
            competitor_values["share_voice"][entity.label][platform] = metrics.get("share_voice")
            competitor_values["citation"][entity.label][platform] = citation_share.get(entity.label)
            competitor_values["average_rank"][entity.label][platform] = metrics.get("average_rank")
            competitor_values["sentiment"][entity.label][platform] = metrics.get("sentiment_score")

        topic_entity_signals = [row for row in platform_signals if row.entity_id == topic_entity.id]
        by_topic = group_signals_by_topic(topic_entity_signals, prompt_to_topic=prompt_to_topic)
        for tid, subset in by_topic.items():
            metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=platform_signals)
            tid_key = str(tid)
            topic_values["visibility"][tid_key][platform] = metrics.visibility_rate
            topic_values["share_voice"][tid_key][platform] = metrics.share_voice
            topic_values["citation"][tid_key][platform] = metrics.citation_rate
            topic_values["average_rank"][tid_key][platform] = metrics.average_rank
            topic_values["sentiment"][tid_key][platform] = metrics.sentiment_score

    platform_series: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for platform in platform_list:
        platform_signals = by_platform_current[platform]
        platform_series[platform] = {
            metric: daily_platform_metric_series_from_signals(
                platform_signals,
                subject=subject,
                entity_id=topic_entity.id,
                field=_METRIC_FIELDS[metric],
            )
            for metric in PLATFORM_MATRIX_METRICS
        }

    return {
        "entity_id": topic_entity.id,
        "own_label": own.label,
        "platforms": platform_list,
        "competitor_rows": competitor_rows,
        "topic_rows": topic_rows,
        "competitor_values": competitor_values,
        "topic_values": topic_values,
        "platform_performance": build_platform_performance(
            db,
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platforms=platforms,
            topic_id=topic_id,
            entity_id=topic_entity.id,
        ),
        "previous_platform_performance": build_platform_performance(
            db,
            subject_id=subject.id,
            dt_from=prev_from,
            dt_to=prev_to,
            platforms=platforms,
            topic_id=topic_id,
            entity_id=topic_entity.id,
        ),
        "platform_series": platform_series,
    }
