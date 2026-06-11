"""Match terms for entity signals (aligned with sampling mentions)."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, competitor_entities, own_entity
from aperix_geo.services.sampling.mentions import (
    collect_match_terms,
    competitor_by_id,
    competitor_entry_from_record,
    own_names,
)


def match_terms_for_entity_signal(
    subject: Subject,
    *,
    entity_id: str,
    entity_kind: str,
    entity_label: str,
    primary_domain: str = "",
) -> list[str]:
    label = (entity_label or "").strip()
    domain = (primary_domain or "").strip()

    if entity_kind == "own" or entity_id == OWN_ENTITY_ID:
        return own_names(subject)

    if entity_kind == "competitor":
        try:
            competitor_id = UUID(entity_id)
        except ValueError:
            return collect_match_terms(label, domain)
        competitor = competitor_by_id(subject).get(competitor_id)
        if competitor is None:
            return collect_match_terms(label, domain)
        for entity in competitor_entities(subject):
            if entity.competitor_id == competitor_id:
                entry = competitor_entry_from_record(entity, competitor)
                return collect_match_terms(label, domain, entry.brand, *entry.terms, *entry.aliases)
        return collect_match_terms(label, domain, competitor.brand, competitor.domain, *(competitor.aliases or []))

    return collect_match_terms(label, domain)
