"""Shared context for LLM prompt generation."""

from __future__ import annotations

from aperix_geo.db.models import Subject
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


def niche_fields_from_scope(scope: dict[str, object] | None) -> tuple[str, str, str]:
    raw = scope if isinstance(scope, dict) else {}
    niche = raw.get("niche_profile")
    profile = niche if isinstance(niche, dict) else {}
    return (
        str(profile.get("industry") or "").strip(),
        str(profile.get("core_features") or "").strip(),
        str(profile.get("target_customers") or "").strip(),
    )


def prompt_context_from_subject(subject: Subject) -> dict[str, object]:
    industry, core_features, target_customers = niche_fields_from_scope(subject.monitoring_scope)
    if not core_features and subject.profile_summary:
        core_features = subject.profile_summary.strip()[:2000]
    entity = (subject.brand or subject.domain or "").strip() or "本品牌"
    domains, brands = competitor_lists(subject)
    return {
        "entity": entity,
        "aliases": entity_aliases(entity=entity, configured=list(subject.aliases or [])),
        "industry": industry,
        "core_features": core_features,
        "target_customers": target_customers,
        "competitors": [*domains, *brands],
    }
