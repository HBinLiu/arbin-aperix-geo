"""Overview dashboard aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.entity_sql import query_entity_window
from aperix_geo.services.brand.analysis import resolve_brand_id_for_analysis_entity

_EMPTY_METRICS = {
    "visibility_rate": None,
    "mention_rate": None,
    "share_voice": None,
    "average_rank": None,
    "citation_rate": None,
    "sentiment_score": None,
    "citation_coverage": None,
}


def build_overview(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    entity = resolve_analysis_entity(subject, entity_id)
    brand_id = resolve_brand_id_for_analysis_entity(db, subject=subject, entity_id=entity_id)
    voice_overview = query_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    focus_overview = query_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        brand_id=brand_id,
    )
    entity_row = next((row for row in focus_overview.entity_rows if row["id"] == entity.id), None)
    metrics = dict(entity_row["metrics"]) if entity_row else dict(_EMPTY_METRICS)
    response_count = int(metrics.get("response_count") or 0)
    mention_total = round((metrics.get("mention_rate") or 0) * response_count)
    metrics["share_voice"] = (
        round(mention_total / voice_overview.total_voice, 4)
        if voice_overview.total_voice > 0
        else None
    )

    return {
        "entity": {
            "id": entity.id,
            "kind": entity.kind,
            "label": entity.label,
            "display_name": entity.display_name,
            "competitor_id": str(entity.competitor_id) if entity.competitor_id else None,
        },
        "window": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
        "filters": {
            "platform": platform or [],
            "topic_id": [str(t) for t in topic_id] if topic_id else None,
            "entity_id": entity.id,
        },
        "visibility_rate": metrics.get("visibility_rate"),
        "mention_rate": metrics.get("mention_rate"),
        "share_voice": metrics.get("share_voice"),
        "average_rank": metrics.get("average_rank"),
        "citation_rate": metrics.get("citation_rate"),
        "sentiment_score": metrics.get("sentiment_score"),
        "citation_coverage": metrics.get("citation_coverage"),
    }
