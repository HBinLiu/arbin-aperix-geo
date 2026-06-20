"""Overview dashboard aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.aggregate import metrics_from_signals
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.brand.analysis import resolve_brand_id_for_analysis_entity
from aperix_geo.services.analysis.signal_load import load_llm_response_signals


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
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    entity_signals = [row for row in all_signals if row.brand_id == brand_id]
    metrics = metrics_from_signals(
        entity_signals,
        subject=subject,
        all_signals_for_voice=all_signals,
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
        "visibility_rate": metrics.visibility_rate,
        "mention_rate": metrics.mention_rate,
        "share_voice": metrics.share_voice,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "sentiment_score": metrics.sentiment_score,
        "citation_coverage": metrics.citation_coverage,
    }
