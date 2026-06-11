"""Unified metrics API builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis.aggregate import aggregate_metrics, sort_metric_rows
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import load_llm_response_signals


def build_analysis_entities(subject: Subject) -> dict[str, Any]:
    return {
        "entities": [
            {
                "id": entity.id,
                "kind": entity.kind,
                "label": entity.label,
                "display_name": entity.display_name,
                "competitor_id": str(entity.competitor_id) if entity.competitor_id else None,
            }
            for entity in list_analysis_entities(subject)
        ]
    }


def build_unified_metrics(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
    group_by: str = "none",
    sort_by: str | None = None,
    order: str = "desc",
) -> dict[str, Any]:
    entity = resolve_analysis_entity(subject, entity_id) if group_by != "entity" else None
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    label_lookup = None
    if group_by == "prompt":
        prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
        prompt_map = {str(p.id): p.text[:200] for p in prompts}
        label_lookup = lambda row_id: prompt_map.get(row_id, row_id)
    elif group_by == "topic":
        topics = db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
        topic_map = {str(t.id): t.name for t in topics}
        label_lookup = lambda row_id: topic_map.get(row_id, row_id)

    aggregated = aggregate_metrics(
        all_signals,
        subject=subject,
        group_by=group_by,  # type: ignore[arg-type]
        entity_id=entity.id if entity else None,
        label_lookup=label_lookup,
    )
    rows = aggregated.rows
    if group_by != "none":
        rows = sort_metric_rows(rows, sort_by=sort_by, order=order)

    entity_payload = None
    if entity:
        entity_payload = {
            "id": entity.id,
            "kind": entity.kind,
            "label": entity.label,
            "display_name": entity.display_name,
            "competitor_id": str(entity.competitor_id) if entity.competitor_id else None,
        }

    totals = aggregated.totals
    return {
        "entity": entity_payload,
        "window": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
        "group_by": group_by,
        "totals": {
            "response_count": totals.response_count,
            "visibility_rate": totals.visibility_rate,
            "mention_rate": totals.mention_rate,
            "share_voice": totals.share_voice,
            "average_rank": totals.average_rank,
            "citation_rate": totals.citation_rate,
            "sentiment_score": totals.sentiment_score,
            "sentiment_count": totals.sentiment_count,
            "citation_coverage": totals.citation_coverage,
        },
        "rows": rows,
    }
