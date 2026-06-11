"""Visibility analysis and topic visibility ranks."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._series import (
    TOPIC_VISIBILITY_RANK_LIMIT,
    align_previous_daily_to_current,
    align_previous_single_series,
    previous_date_range,
    slim_daily_series,
    top_visibility_labels,
)
from aperix_geo.services.analysis.aggregate import (
    daily_average_rank_series_from_signals,
    daily_share_series_from_signals,
    group_signals_by_topic,
    top_entity_labels_by_visibility,
)
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.rank import build_rank
from aperix_geo.services.analysis.signal_load import load_llm_response_signals


def build_topic_visibility_ranks(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """各主题下按可见度排序的品牌 Top5（用于主题可见度排名表）。"""
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
    )
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
    }
    prompt_to_topic = {pid: p.topic_id for pid, p in prompts.items()}
    by_topic = group_signals_by_topic(all_signals, prompt_to_topic=prompt_to_topic)

    out: list[dict[str, Any]] = []
    for tid in sorted(topics.keys(), key=lambda k: topics[k].name):
        t = topics[tid]
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": t.name,
                "ranks": top_entity_labels_by_visibility(
                    by_topic.get(tid, []),
                    subject=subject,
                    limit=TOPIC_VISIBILITY_RANK_LIMIT,
                ),
            }
        )
    return out


def build_visibility_analysis(
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
    """Rank + daily 序列，并附带上一周期 rank 与选定实体对齐 daily 序列。"""
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

    rank = build_rank(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    prev_rank = build_rank(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=prev_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    labels = top_visibility_labels(rank["visibility_share"], rank["own_label"])
    share_voice_labels = top_visibility_labels(rank["share_voice"], rank["own_label"])
    series = slim_daily_series(
        daily_share_series_from_signals(current_signals, subject=subject, metric="visibility"),
        labels,
    )
    mention_series = slim_daily_series(
        daily_share_series_from_signals(current_signals, subject=subject, metric="mention"),
        labels,
    )
    average_rank_series = daily_average_rank_series_from_signals(
        current_signals,
        entity_id=entity.id,
    )
    focus_label = entity.label

    return {
        "entity_id": entity.id,
        "own_label": rank["own_label"],
        "focus_label": focus_label,
        "labels": labels,
        "share_voice_labels": share_voice_labels,
        "rank": rank,
        "series": series,
        "mention_series": mention_series,
        "average_rank_series": average_rank_series,
        "previous_rank": prev_rank,
        "previous_series": align_previous_daily_to_current(
            series,
            daily_share_series_from_signals(prev_signals, subject=subject, metric="visibility"),
            [focus_label],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "previous_mention_series": align_previous_daily_to_current(
            mention_series,
            daily_share_series_from_signals(prev_signals, subject=subject, metric="mention"),
            [focus_label],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "previous_average_rank_series": align_previous_single_series(
            average_rank_series,
            daily_average_rank_series_from_signals(prev_signals, entity_id=entity.id),
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "topic_visibility_ranks": build_topic_visibility_ranks(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platforms=platforms,
        ),
    }
