"""Overview dashboard aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.metrics import compute_subject_metrics


def build_overview(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    metrics = compute_subject_metrics(rows, subject=subject)
    return {
        "window": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
        "filters": {
            "platforms": platforms or [],
            "topic_id": str(topic_id) if topic_id else None,
        },
        "visibility_rate": metrics.visibility_rate,
        "mention_rate": metrics.mention_rate,
        "share_voice": metrics.share_voice,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
        "citation_coverage": metrics.citation_coverage,
    }
