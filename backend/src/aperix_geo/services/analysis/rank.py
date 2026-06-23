"""Brand rank board — flat entity rows for the dashboard rank page."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import list_analysis_entities, own_entity
from aperix_geo.services.analysis.entity_sql import query_entity_window


def _rank_item(row: dict[str, Any], *, domain: str) -> dict[str, Any]:
    metrics = row["metrics"]
    return {
        "entity_id": row["id"],
        "label": row["label"],
        "display_name": row["display_name"],
        "domain": domain,
        "is_own": row["is_own"],
        "visibility_rate": metrics.get("visibility_rate"),
        "mention_rate": metrics.get("mention_rate"),
        "share_voice": metrics.get("share_voice"),
        "average_rank": metrics.get("average_rank"),
        "citation_rate": metrics.get("citation_rate"),
        "sentiment_score": metrics.get("sentiment_score"),
        "sentiment_label": metrics.get("sentiment_label"),
    }


def build_rank(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, object]:
    """Return sorted rank-board rows (own + configured competitors) via SQL aggregation."""
    entities = list_analysis_entities(subject)
    domain_by_id = {entity.id: entity.domain for entity in entities}
    overview = query_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    items = [
        _rank_item(row, domain=domain_by_id.get(row["id"], ""))
        for row in overview.entity_rows
    ]
    items.sort(key=lambda row: -(row.get("visibility_rate") or 0))
    own = own_entity(subject)
    return {
        "own_label": own.label,
        "items": items,
    }
