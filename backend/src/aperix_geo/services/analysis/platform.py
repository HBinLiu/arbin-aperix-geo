"""Platform matrix analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._labels import own_label, rank_labels
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.citation import citation_share_by_label
from aperix_geo.services.analysis.metrics import (
    compute_subject_metrics,
    daily_platform_metric_series,
    platform_metrics_from_rows,
)
from aperix_geo.services.analysis.rank import rank_from_rows

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
) -> dict[str, Any]:
    """平台矩阵：竞争对手/主题 × 平台 × 指标，含平台排名与分平台趋势。"""
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    current_rows = [r for r in rows if dt_from <= r.created_at <= dt_to]
    prev_rows = [r for r in rows if prev_from <= r.created_at <= prev_to]

    own = own_label(subject)
    labels = rank_labels(subject)
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
    }

    by_platform_current: dict[str, list] = defaultdict(list)
    for r in current_rows:
        by_platform_current[r.platform].append(r)
    by_platform_prev: dict[str, list] = defaultdict(list)
    for r in prev_rows:
        by_platform_prev[r.platform].append(r)

    platform_list = sorted(by_platform_current.keys())
    competitor_rows = [{"id": lab, "label": lab, "is_own": lab == own} for lab in labels]
    topic_rows = [{"id": str(tid), "label": topics[tid].name} for tid in sorted(topics.keys(), key=lambda k: topics[k].name)]

    competitor_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {lab: {} for lab in labels} for metric in PLATFORM_MATRIX_METRICS
    }
    topic_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {str(tid): {} for tid in topics} for metric in PLATFORM_MATRIX_METRICS
    }

    for platform, prows in by_platform_current.items():
        rank = rank_from_rows(prows, subject=subject)
        citation = citation_share_by_label(prows, subject=subject, labels=labels)
        own_metrics = compute_subject_metrics(prows, subject=subject)

        for lab in labels:
            competitor_values["visibility"][lab][platform] = rank["visibility_share"].get(lab)
            competitor_values["share_voice"][lab][platform] = rank["share_voice"].get(lab)
            competitor_values["citation"][lab][platform] = citation.get(lab)
            competitor_values["average_rank"][lab][platform] = rank["average_rank"].get(lab)
            competitor_values["sentiment"][lab][platform] = (
                own_metrics.sentiment_score if lab == own else None
            )

        by_topic: dict[UUID, list] = defaultdict(list)
        for r in prows:
            prompt = prompts.get(r.prompt_id)
            if prompt:
                by_topic[prompt.topic_id].append(r)
        for tid, trows in by_topic.items():
            metrics = compute_subject_metrics(trows, subject=subject)
            tid_key = str(tid)
            topic_values["visibility"][tid_key][platform] = metrics.visibility_rate
            topic_values["share_voice"][tid_key][platform] = metrics.share_voice
            topic_values["citation"][tid_key][platform] = metrics.citation_rate
            topic_values["average_rank"][tid_key][platform] = metrics.average_rank
            topic_values["sentiment"][tid_key][platform] = metrics.sentiment_score

    platform_series: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for platform in platform_list:
        prows = by_platform_current[platform]
        platform_series[platform] = {
            metric: daily_platform_metric_series(prows, subject=subject, field=_METRIC_FIELDS[metric])
            for metric in PLATFORM_MATRIX_METRICS
        }

    return {
        "own_label": own,
        "platforms": platform_list,
        "competitor_rows": competitor_rows,
        "topic_rows": topic_rows,
        "competitor_values": competitor_values,
        "topic_values": topic_values,
        "platform_performance": platform_metrics_from_rows(by_platform_current, subject=subject),
        "previous_platform_performance": platform_metrics_from_rows(by_platform_prev, subject=subject),
        "platform_series": platform_series,
    }
