"""Diagnosis center aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis._labels import own_label, rank_labels
from aperix_geo.services.analysis._parsed import competitors_mentioned, mentions_own
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.metrics import compute_subject_metrics


def diagnosis_priority(mention_rate: float | None, average_rank: float | None) -> str:
    issue = diagnosis_issue_type(mention_rate, average_rank)
    if issue == "not_mentioned":
        return "high"
    if issue in ("low_mention", "poor_rank"):
        return "medium"
    return "low"


def diagnosis_issue_type(mention_rate: float | None, average_rank: float | None) -> str:
    rate = mention_rate or 0
    if rate <= 0:
        return "not_mentioned"
    if rate < 0.5:
        return "low_mention"
    if average_rank is not None and average_rank > 3:
        return "poor_rank"
    return "healthy"


def priority_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        key = item.get("priority")
        if key in counts:
            counts[key] += 1
    return counts


def health_score_from_mention(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    total = sum((item.get("mention_rate") or 0) for item in items)
    return round(total / len(items) * 100, 1)


def health_score_from_prompt(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    total = sum((item.get("mention_rate") or 0) for item in items)
    return round(total / len(items) * 100, 1)


def overall_diagnosis_status(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "needs_improvement"
    return "critical"


def build_diagnosis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    """诊断中心：整体得分、维度健康分与提示词 × 平台诊断明细。"""
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    own = own_label(subject)
    labels = rank_labels(subject)
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    grouped: dict[tuple[UUID, str], list] = defaultdict(list)
    prompt_rows: dict[UUID, list] = defaultdict(list)
    for row in rows:
        grouped[(row.prompt_id, row.platform)].append(row)
        prompt_rows[row.prompt_id].append(row)

    mention_items: list[dict[str, Any]] = []
    for (prompt_id, platform), prows in grouped.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue
        metrics = compute_subject_metrics(prows, subject=subject)
        total = len(prows)
        mention_own = sum(1 for row in prows if mentions_own(row.parsed or {}))
        mention_rate = metrics.mention_rate

        competitors: list[str] = []
        seen: set[str] = set()
        for row in prows:
            if mentions_own(row.parsed or {}):
                continue
            for lab in competitors_mentioned(row.parsed or {}, labels=labels, own=own):
                if lab not in seen:
                    seen.add(lab)
                    competitors.append(lab)

        mention_items.append(
            {
                "id": f"{prompt_id}:{platform}",
                "prompt_id": str(prompt_id),
                "prompt_text": prompt.text,
                "platform": platform,
                "priority": diagnosis_priority(mention_rate, metrics.average_rank),
                "mention_rate": mention_rate or 0,
                "mention_own_count": mention_own,
                "mention_total_count": total,
                "average_rank": metrics.average_rank,
                "issue_type": diagnosis_issue_type(mention_rate, metrics.average_rank),
                "competitors": competitors,
            }
        )

    prompt_items: list[dict[str, Any]] = []
    for prompt_id, prows in prompt_rows.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue
        metrics = compute_subject_metrics(prows, subject=subject)
        total = len(prows)
        mention_own = sum(1 for row in prows if mentions_own(row.parsed or {}))
        mention_rate = metrics.mention_rate

        prompt_items.append(
            {
                "id": str(prompt_id),
                "prompt_id": str(prompt_id),
                "prompt_text": prompt.text,
                "priority": diagnosis_priority(mention_rate, metrics.average_rank),
                "mention_rate": mention_rate or 0,
                "mention_own_count": mention_own,
                "mention_total_count": total,
                "average_rank": metrics.average_rank,
                "issue_type": diagnosis_issue_type(mention_rate, metrics.average_rank),
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    mention_items.sort(
        key=lambda row: (
            priority_order.get(row["priority"], 9),
            row["mention_rate"],
            row.get("average_rank") or 999,
        )
    )
    prompt_items.sort(
        key=lambda row: (
            priority_order.get(row["priority"], 9),
            row["mention_rate"],
            row.get("average_rank") or 999,
        )
    )

    mention_health = health_score_from_mention(mention_items)
    prompt_health = health_score_from_prompt(prompt_items)
    overall_score = round(mention_health * 0.6 + prompt_health * 0.4, 1)

    return {
        "overall_score": overall_score,
        "overall_status": overall_diagnosis_status(overall_score),
        "dimensions": {
            "mention": {
                "health_score": mention_health,
                "priority_counts": priority_counts(mention_items),
            },
            "prompt": {
                "health_score": prompt_health,
                "priority_counts": priority_counts(prompt_items),
            },
        },
        "mention_items": mention_items,
        "prompt_items": prompt_items,
    }
