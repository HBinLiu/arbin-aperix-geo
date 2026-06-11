"""Brand rank and share-of-voice aggregates."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject


def build_rank(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, object]:
    from aperix_geo.services.analysis.aggregate import aggregate_metrics, rank_dict_from_entity_rows
    from aperix_geo.services.analysis.entity import own_entity
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    aggregated = aggregate_metrics(all_signals, subject=subject, group_by="entity")
    own = own_entity(subject)
    return rank_dict_from_entity_rows(aggregated.rows, own_label=own.label)
