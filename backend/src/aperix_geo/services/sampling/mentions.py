"""Brand mention detection and rank hints from LLM response text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.services.subject.labels import competitor_rank_label, own_label
from aperix_geo.utils.url import host_matches_root, normalize_domain


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


def _competitor_entry(competitor: Competitor) -> CompetitorEntry | None:
    brand = (competitor.brand or "").strip()
    domain = (competitor.domain or "").strip()
    label = competitor_rank_label(brand=brand, domain=domain)
    if not label:
        return None
    alias_list = [str(x).strip() for x in (competitor.aliases or []) if str(x).strip()]
    terms = collect_match_terms(brand, domain, *alias_list)
    return CompetitorEntry(
        label=label,
        brand=brand,
        terms=tuple(terms),
        domain=domain,
        aliases=tuple(alias_list),
    )


def competitor_entries(subject: Subject) -> list[CompetitorEntry]:
    entries: list[CompetitorEntry] = []
    seen: set[str] = set()
    for competitor in subject.competitors or []:
        entry = _competitor_entry(competitor)
        if not entry:
            continue
        key = entry.label.lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
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


def _count_terms(text: str, terms: list[str] | tuple[str, ...]) -> int:
    return sum(count_term(text, term) for term in terms if term)


def _host_mentions_domain(domain: str, url_hosts: list[str]) -> bool:
    if not domain or not url_hosts:
        return False
    root = normalize_domain(domain) or domain.lower()
    label = domain.split(".")[0].lower()
    for host in url_hosts:
        host_lower = (host or "").lower()
        if label in host_lower or host_matches_root(host, root):
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


def parse_competitor_mentions(
    text: str,
    url_hosts: list[str],
    competitors: list[CompetitorEntry],
) -> tuple[dict[str, bool], dict[str, int]]:
    mentions: dict[str, bool] = {}
    counts: dict[str, int] = {}
    for entry in competitors:
        count = _count_terms(text, entry.terms)
        host_hit = _host_mentions_domain(entry.domain, url_hosts)
        if count == 0 and host_hit:
            count = 1
        mentions[entry.label] = count > 0 or host_hit
        counts[entry.label] = count
    return mentions, counts


def compute_rank_own(
    raw_text: str,
    *,
    subject: Subject,
    competitors: list[CompetitorEntry],
) -> int | None:
    """Rank by first occurrence index among all mentioned candidates."""
    candidates: list[tuple[str, int]] = []
    for name in own_names(subject):
        idx = _first_idx(raw_text, name)
        if idx is not None:
            candidates.append((name, idx))
    for entry in competitors:
        idx = first_idx_any(raw_text, entry.terms)
        if idx is not None:
            candidates.append((entry.label, idx))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1])
    own_set = {name.lower() for name in own_names(subject)}
    for rank, (name, _) in enumerate(candidates, start=1):
        if name.lower() in own_set:
            return rank
    return None


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


def _absa_brand_mentioned(brands: dict[str, Any], key: str) -> bool | None:
    entry = brands.get(key)
    if not isinstance(entry, dict) or "mentioned" not in entry:
        return None
    return bool(entry.get("mentioned"))


def merge_absa_mention_flags(
    mention_stats: dict[str, Any],
    response_absa: dict[str, Any],
    *,
    own_brand: str,
    competitor_absa_keys: list[tuple[str, str]],
    url_hosts: list[str] | None = None,
    competitors: list[CompetitorEntry] | None = None,
) -> dict[str, Any]:
    """Align mention booleans/counts with response ABSA when analysis succeeded."""
    if response_absa.get("analysis_source") != "llm":
        return mention_stats

    brands = response_absa.get("brands_sentiment_absa")
    if not isinstance(brands, dict):
        return mention_stats

    stats = dict(mention_stats)
    own_flag = _absa_brand_mentioned(brands, own_brand)
    if own_flag is True:
        stats["mentions_own"] = True
        if int(stats.get("mention_count_own") or 0) == 0:
            stats["mention_count_own"] = 1
    elif own_flag is False:
        stats["mentions_own"] = False
        stats["mention_count_own"] = 0

    mentions_comp = dict(stats.get("mentions_competitors") or {})
    counts_comp = dict(stats.get("mention_counts_competitors") or {})
    entries_by_label = {entry.label: entry for entry in (competitors or [])}

    keys_by_label: dict[str, list[str]] = {}
    for absa_key, output_label in competitor_absa_keys:
        keys_by_label.setdefault(output_label, []).append(absa_key)

    for output_label, keys in keys_by_label.items():
        flags = [_absa_brand_mentioned(brands, key) for key in keys]
        resolved = [flag for flag in flags if flag is not None]
        if not resolved:
            continue
        if any(resolved):
            mentions_comp[output_label] = True
            if int(counts_comp.get(output_label) or 0) == 0:
                counts_comp[output_label] = 1
        else:
            entry = entries_by_label.get(output_label)
            host_only = (
                bool(mentions_comp.get(output_label))
                and int(counts_comp.get(output_label) or 0) == 0
                and entry is not None
                and _host_mentions_domain(entry.domain, url_hosts or [])
            )
            if host_only:
                continue
            mentions_comp[output_label] = False
            counts_comp[output_label] = 0

    stats["mentions_competitors"] = mentions_comp
    stats["mention_counts_competitors"] = counts_comp
    return stats


def parse_mentions_and_rank(
    text: str,
    *,
    subject: Subject,
    url_hosts: list[str],
) -> dict:
    """Own/competitor mentions, counts, rank hints, and competitor entries."""
    names = own_names(subject)
    mention_count_own = sum(count_term(text, name) for name in names if name)
    competitors = competitor_entries(subject)
    mentions_competitors, mention_counts_competitors = parse_competitor_mentions(
        text,
        url_hosts,
        competitors,
    )
    subject_label = own_label(subject)
    rank_hints: dict[str, int | None] = {subject_label: first_idx_any(text, names)}
    for entry in competitors:
        rank_hints[entry.label] = first_idx_any(text, entry.terms)

    return {
        "own_names": names,
        "own_label": subject_label,
        "competitors": competitors,
        "mentions_own": mention_count_own > 0,
        "mention_count_own": mention_count_own,
        "mentions_competitors": mentions_competitors,
        "mention_counts_competitors": mention_counts_competitors,
        "rank_hints_first_index": rank_hints,
        "rank_own": compute_rank_own(text, subject=subject, competitors=competitors),
    }
