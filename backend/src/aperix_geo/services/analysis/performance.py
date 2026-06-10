"""Topic, prompt, and platform performance tables."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.metrics import compute_subject_metrics


def build_topics_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> list[dict[str, Any]]:
    rows = responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    topic_ids: dict[UUID, list] = defaultdict(list)
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    for r in rows:
        p = prompts.get(r.prompt_id)
        if not p:
            continue
        topic_ids[p.topic_id].append(r)

    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for tid, trows in topic_ids.items():
        t = topics.get(tid)
        name = t.name if t else str(tid)
        metrics = compute_subject_metrics(trows, subject=subject) if subject else None
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": name,
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_rate": metrics.mention_rate if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
                "response_count": metrics.response_count if metrics else 0,
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
) -> list[dict[str, Any]]:
    rows = responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    by_prompt: dict[UUID, list] = defaultdict(list)
    for r in rows:
        by_prompt[r.prompt_id].append(r)
    prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    pmap = {p.id: p for p in prompts}
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for pid, prows in by_prompt.items():
        p = pmap.get(pid)
        text = p.text if p else ""
        topic = topics.get(p.topic_id) if p else None
        metrics = compute_subject_metrics(prows, subject=subject) if subject else None
        out.append(
            {
                "prompt_id": str(pid),
                "prompt_text": text[:200],
                "topic_id": str(p.topic_id) if p else None,
                "topic_name": topic.name if topic else None,
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_rate": metrics.mention_rate if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
                "response_count": metrics.response_count if metrics else 0,
            }
        )
    return sorted(out, key=lambda x: x["prompt_text"])


def build_platform_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> list[dict[str, Any]]:
    rows = responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    by_platform: dict[str, list] = defaultdict(list)
    for r in rows:
        by_platform[r.platform].append(r)

    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for platform, mrows in by_platform.items():
        metrics = compute_subject_metrics(mrows, subject=subject) if subject else None
        out.append(
            {
                "platform": platform,
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_rate": metrics.mention_rate if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))
