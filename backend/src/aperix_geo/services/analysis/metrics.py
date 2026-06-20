"""KPI metric bundle and entity catalog builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import list_analysis_entities


@dataclass
class MetricsBundle:
    response_count: int
    visibility_rate: float | None
    mention_rate: float | None
    share_voice: float | None
    average_rank: float | None
    citation_rate: float | None
    sentiment_score: float | None
    sentiment_label: str | None = None
    citation_coverage: float | None = None


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
