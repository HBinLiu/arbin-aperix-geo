"""Brand mention detection and rank hints from LLM response text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.utils.net import host_from, host_under_root, registrable_from

if TYPE_CHECKING:
    from aperix_geo.services.analysis.entity import AnalysisEntity


@dataclass(frozen=True)
class CompetitorEntry:
    label: str
    brand: str
    terms: tuple[str, ...]
    domain: str
    aliases: tuple[str, ...] = ()


def collect_match_terms(*parts: str | None) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for term in parts:
        text = (term or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(text)
    return names


def own_names(subject: Subject) -> list[str]:
    """主体提及匹配词：brand、domain、aliases 均参与（两种 Subject.type 一致）。"""
    return collect_match_terms(
        subject.brand,
        subject.domain,
        *(str(x) for x in (subject.aliases or []) if x),
    )


def competitor_by_id(subject: Subject) -> dict[UUID, Competitor]:
    return {competitor.id: competitor for competitor in (subject.competitors or [])}


def competitor_entry_from_record(entity: AnalysisEntity, competitor: Competitor) -> CompetitorEntry:
    brand = (competitor.brand or "").strip()
    domain = (competitor.domain or "").strip()
    alias_list = [str(x).strip() for x in (competitor.aliases or []) if str(x).strip()]
    terms = collect_match_terms(brand, domain, *alias_list)
    return CompetitorEntry(
        label=entity.label,
        brand=brand,
        terms=tuple(terms),
        domain=domain,
        aliases=tuple(alias_list),
    )


def competitor_entries(subject: Subject) -> list[CompetitorEntry]:
    from aperix_geo.services.analysis.entity import competitor_entities

    by_id = competitor_by_id(subject)
    entries: list[CompetitorEntry] = []
    for entity in competitor_entities(subject):
        if entity.competitor_id is None:
            continue
        competitor = by_id.get(entity.competitor_id)
        if competitor is None:
            continue
        entries.append(competitor_entry_from_record(entity, competitor))
    return entries


def count_term(text: str, term: str) -> int:
    if not term or not text:
        return 0
    lowered = text.lower()
    needle = term.lower()
    count = start = 0
    while True:
        idx = lowered.find(needle, start)
        if idx < 0:
            break
        count += 1
        start = idx + len(needle)
    return count


def host_mentions_domain(domain: str, url_hosts: list[str]) -> bool:
    if not domain or not url_hosts:
        return False
    root = registrable_from(domain) or host_from(domain)
    label = domain.split(".")[0].lower()
    for host in url_hosts:
        host_lower = (host or "").lower()
        if label in host_lower or host_under_root(host, root):
            return True
    return False


def _first_idx(text: str, term: str) -> int | None:
    if not term:
        return None
    idx = text.lower().find(term.lower())
    return idx if idx >= 0 else None


def first_idx_any(text: str, terms: list[str] | tuple[str, ...]) -> int | None:
    indices = [_first_idx(text, term) for term in terms if term]
    valid = [idx for idx in indices if idx is not None]
    return min(valid) if valid else None


def _absa_keys_for_entry(entry: CompetitorEntry) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for term in [entry.brand, entry.label, *entry.aliases, *entry.terms]:
        text = (term or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def absa_competitor_keys(
    competitors: list[CompetitorEntry],
) -> tuple[list[str], list[tuple[str, str]]]:
    """Unique ABSA brand keys and (absa_key, output_label) pairs for sentiment mapping."""
    competitor_brand_names: list[str] = []
    competitor_absa_keys: list[tuple[str, str]] = []
    seen_absa_keys: set[str] = set()
    for entry in competitors:
        for absa_key in _absa_keys_for_entry(entry):
            competitor_absa_keys.append((absa_key, entry.label))
            if absa_key not in seen_absa_keys:
                seen_absa_keys.add(absa_key)
                competitor_brand_names.append(absa_key)
    return competitor_brand_names, competitor_absa_keys


def absa_brand_mentioned(brands: dict[str, Any], key: str) -> bool | None:
    entry = brands.get(key)
    if not isinstance(entry, dict) or "mentioned" not in entry:
        return None
    return bool(entry.get("mentioned"))
