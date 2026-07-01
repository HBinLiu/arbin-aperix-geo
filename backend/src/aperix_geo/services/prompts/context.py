"""Shared context for LLM prompt generation."""

from __future__ import annotations

from aperix_geo.db.models import Subject
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.subject.loader import competitor_lists


def entity_aliases(
    *,
    entity: str,
    configured: list[str] | None = None,
    profile_company: str | None = None,
) -> list[str]:
    """Brand aliases for generation; excludes the primary entity label."""
    entity_key = entity.strip().casefold()
    seen: set[str] = set()
    out: list[str] = []
    for term in [*(configured or []), profile_company or ""]:
        label = str(term or "").strip()
        if not label:
            continue
        key = label.casefold()
        if key == entity_key or key in seen:
            continue
        seen.add(key)
        out.append(label)
    return out


def prompt_context_from_subject(subject: Subject) -> dict[str, object]:
    profile: NicheProfile = profile_from_dict(dict(subject.niche_profile or {}))
    entity = (subject.brand or subject.domain or "").strip() or "本品牌"
    domains, brands = competitor_lists(subject)
    features = str(profile.get("features") or "").strip()
    if not features and subject.profile_summary:
        features = subject.profile_summary.strip()[:2000]
    return {
        "entity": entity,
        "aliases": entity_aliases(
            entity=entity,
            configured=list(subject.aliases or []),
            profile_company=str(profile.get("company") or ""),
        ),
        "industry": str(profile.get("industry") or ""),
        "features": features,
        "customers": str(profile.get("customers") or ""),
        "competitors": [*domains, *brands],
        "profile": profile,
    }
