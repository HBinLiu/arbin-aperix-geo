"""Diagnosis center aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis.aggregate import metrics_from_signals, other_mentioned_entity_labels
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals


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


def _response_ids(signals: list[LLMResponseSignalRow]) -> set[UUID]:
    return {row.response_id for row in signals}


def build_diagnosis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """诊断中心：整体得分、维度健康分与提示词 × 平台诊断明细。"""
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    entity_signals = [row for row in all_signals if row.entity_id == entity.id]
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    grouped: dict[tuple[UUID, str], list[LLMResponseSignalRow]] = defaultdict(list)
    prompt_rows: dict[UUID, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in entity_signals:
        grouped[(row.prompt_id, row.platform)].append(row)
        prompt_rows[row.prompt_id].append(row)

    mention_items: list[dict[str, Any]] = []
    for (prompt_id, platform), subset in grouped.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue
        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        total = metrics.response_count
        mention_own = sum(1 for row in subset if row.mentioned)
        mention_rate = metrics.mention_rate

        competitors = other_mentioned_entity_labels(
            _response_ids(subset),
            all_signals=all_signals,
            exclude_entity_id=entity.id,
            subject=subject,
        )

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
    for prompt_id, subset in prompt_rows.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue
        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        total = metrics.response_count
        mention_own = sum(1 for row in subset if row.mentioned)
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
        "entity_id": entity.id,
        "entity_label": entity.label,
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
