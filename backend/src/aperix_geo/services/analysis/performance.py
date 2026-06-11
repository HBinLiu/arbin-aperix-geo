"""Topic, prompt, and platform performance tables."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis.aggregate import (
    aggregate_metrics,
    group_signals_by_topic,
    metrics_from_signals,
)
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import load_llm_response_signals


def build_topics_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return []
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
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    }
    prompt_to_topic = {pid: p.topic_id for pid, p in prompts.items()}
    grouped = group_signals_by_topic(entity_signals, prompt_to_topic=prompt_to_topic)

    out: list[dict[str, Any]] = []
    for tid, subset in grouped.items():
        topic = topics.get(tid)
        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": topic.name if topic else str(tid),
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "response_count": metrics.response_count,
            }
        )
    return sorted(out, key=lambda x: x["topic_name"])


def build_prompts_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    entity_id: str | None = None,
    sort_by: str | None = None,
    order: str = "desc",
) -> list[dict[str, Any]]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return []
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
    prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    pmap = {p.id: p for p in prompts}
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }

    by_prompt: dict[UUID, list] = defaultdict(list)
    for row in entity_signals:
        by_prompt[row.prompt_id].append(row)

    metric_rows: list[dict[str, Any]] = []
    for pid, subset in by_prompt.items():
        prompt = pmap.get(pid)
        topic = topics.get(prompt.topic_id) if prompt else None
        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        metric_rows.append(
            {
                "prompt_id": str(pid),
                "prompt_text": (prompt.text[:200] if prompt else ""),
                "topic_id": str(prompt.topic_id) if prompt else None,
                "topic_name": topic.name if topic else None,
                "funnel_stage": prompt.funnel_stage if prompt else None,
                "search_intent": prompt.search_intent if prompt else None,
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "response_count": metrics.response_count,
            }
        )

    if sort_by:
        reverse = order != "asc"
        if sort_by == "average_rank":
            reverse = order == "asc"

        def sort_key(row: dict[str, Any]) -> float:
            value = row.get(sort_by)
            if value is None:
                return float("inf") if sort_by == "average_rank" else (float("-inf") if reverse else float("inf"))
            return float(value)

        metric_rows.sort(key=sort_key, reverse=reverse)
        return metric_rows

    return sorted(metric_rows, key=lambda x: -(x["visibility_rate"] or 0))


def build_platform_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return []
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    entity_signals = [row for row in all_signals if row.entity_id == entity.id]
    aggregated = aggregate_metrics(
        entity_signals,
        subject=subject,
        group_by="platform",
        entity_id=entity.id,
    )
    out: list[dict[str, Any]] = []
    for row in aggregated.rows:
        metrics = row["metrics"]
        out.append(
            {
                "platform": row["id"],
                "visibility_rate": metrics["visibility_rate"],
                "mention_rate": metrics["mention_rate"],
                "share_voice": metrics["share_voice"],
                "average_rank": metrics["average_rank"],
                "citation_rate": metrics["citation_rate"],
                "sentiment_score": metrics["sentiment_score"],
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))
