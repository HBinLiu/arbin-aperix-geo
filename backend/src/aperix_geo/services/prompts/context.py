"""Shared context for LLM prompt generation."""

from __future__ import annotations

from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.competitor.profile import keywords_list, profile_from_dict
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


def keywords_canonical(profile: NicheProfile) -> str:
    """Hash / cache 用的 keywords 归一化串（与 LLM list 同源）。"""
    return "、".join(keywords_list(profile))


def prompt_context_from_subject(subject: Subject) -> dict[str, object]:
    profile: NicheProfile = profile_from_dict(dict(subject.niche_profile or {}))
    entity = (subject.brand or subject.domain or "").strip() or "本品牌"
    domains, brands = competitor_lists(subject)
    return {
        "entity": entity,
        "aliases": entity_aliases(
            entity=entity,
            configured=list(subject.aliases or []),
            profile_company=str(profile.get("company") or ""),
        ),
        "industry": str(profile.get("industry") or ""),
        "keywords": keywords_canonical(profile),
        "brief": str(profile.get("brief") or ""),
        "competitors": [*domains, *brands],
        "profile": profile,
    }


def prompt_context_from_session(
    session: dict[str, Any],
    *,
    topics: list[str],
    exclude_prompts: list[str] | None = None,
    competitor_labels: list[str],
) -> dict[str, Any]:
    """Setup session → 与 subject 对齐的提示词生成上下文。"""
    entity = str(session.get("target") or "").strip()
    if not entity:
        raise ValueError("setup session missing target")

    profile = profile_from_dict(session.get("profile") or {})
    return {
        "entity": entity,
        "confirmed_topics": topics,
        "profile": profile,
        "industry": str(profile.get("industry") or ""),
        "keywords": keywords_canonical(profile),
        "brief": str(profile.get("brief") or ""),
        "aliases": entity_aliases(
            entity=entity,
            profile_company=str(profile.get("company") or ""),
        ),
        "competitors": competitor_labels,
        "excluded": [p.strip() for p in (exclude_prompts or []) if p.strip()],
    }
