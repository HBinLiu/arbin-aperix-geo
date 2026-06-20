"""Analysis entity catalog (own brand + configured competitors)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status

from aperix_geo.db.models import Subject
from aperix_geo.services.subject.labels import (
    competitor_rank_domain,
    competitor_rank_label,
    own_label,
    subject_rank_domain,
)

OWN_ENTITY_ID = "own"


@dataclass(frozen=True)
class AnalysisEntity:
    id: str
    kind: Literal["own", "competitor"]
    label: str
    display_name: str
    domain: str
    competitor_id: UUID | None = None


def own_entity(subject: Subject) -> AnalysisEntity:
    label = own_label(subject)
    display = (subject.brand or subject.domain or label).strip() or label
    return AnalysisEntity(
        id=OWN_ENTITY_ID,
        kind="own",
        label=label,
        display_name=display,
        domain=subject_rank_domain(subject),
        competitor_id=None,
    )


def competitor_entities(subject: Subject) -> list[AnalysisEntity]:
    out: list[AnalysisEntity] = []
    seen: set[str] = set()
    for competitor in subject.competitors or []:
        label = competitor_rank_label(brand=competitor.brand or "", domain=competitor.domain or "")
        if not label or label in seen:
            continue
        seen.add(label)
        display = (competitor.brand or competitor.domain or label).strip() or label
        out.append(
            AnalysisEntity(
                id=str(competitor.id),
                kind="competitor",
                label=label,
                display_name=display,
                domain=competitor_rank_domain(domain=competitor.domain or ""),
                competitor_id=competitor.id,
            )
        )
    return out


def list_analysis_entities(subject: Subject) -> list[AnalysisEntity]:
    return [own_entity(subject), *competitor_entities(subject)]


def entity_chart_labels(entities: list[AnalysisEntity]) -> list[str]:
    """Stable chart series keys in catalog order (not metric-ranked)."""
    return [entity.label for entity in entities]


def resolve_analysis_entity(subject: Subject, entity_id: str | None) -> AnalysisEntity:
    eid = entity_id or OWN_ENTITY_ID
    for entity in list_analysis_entities(subject):
        if entity.id == eid:
            return entity
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown analysis entity: {entity_id}",
    )
