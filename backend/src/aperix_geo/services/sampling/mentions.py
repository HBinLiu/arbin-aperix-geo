"""Brand mention detection and rank hints from LLM response text."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM,
    citation_response_mention_discovery_user_content,
)
from aperix_geo.services.sampling.cache.mention_discovery import (
    get_mention_discovery_cached,
    mention_discovery_cache_digest,
    set_mention_discovery_cached,
)
from aperix_geo.services.sampling.mention_entities import ValidatedMention, parse_discovery_entities
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight
from aperix_geo.utils.json import extract_json_object
from aperix_geo.utils.net import host_from, host_under_root, registrable_from

if TYPE_CHECKING:
    from aperix_geo.services.analysis.entity import AnalysisEntity

logger = logging.getLogger(__name__)


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
    if not root:
        return False
    for host in url_hosts:
        if host_under_root(host, root):
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


def absa_own_keys(
    *,
    own_brand: str,
    own_match_names: list[str],
    entity_label: str,
) -> tuple[list[str], list[tuple[str, str]]]:
    """主体闭集 ABSA 键（含 aliases），均映射到 entity_label。"""
    own_brand_names: list[str] = []
    own_absa_keys: list[tuple[str, str]] = []
    seen_absa_keys: set[str] = set()
    label = (entity_label or own_brand or "").strip()
    for absa_key in _absa_keys_for_terms(own_brand, label, own_match_names):
        own_absa_keys.append((absa_key, label))
        if absa_key not in seen_absa_keys:
            seen_absa_keys.add(absa_key)
            own_brand_names.append(absa_key)
    return own_brand_names, own_absa_keys


def _absa_keys_for_terms(brand: str, label: str, extra_terms: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for term in [brand, label, *extra_terms]:
        text = (term or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def _absa_keys_for_entry(entry: CompetitorEntry) -> list[str]:
    return _absa_keys_for_terms(entry.brand, entry.label, [*entry.aliases, *entry.terms])


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


def _entities_to_cache(entities: list[ValidatedMention]) -> list[dict[str, Any]]:
    return [
        {
            "text": entity.text,
            "type": entity.entity_type,
            "start": entity.start,
            "end": entity.end,
        }
        for entity in entities
    ]


def _entities_from_cache(raw: list[dict[str, Any]], raw_text: str) -> list[ValidatedMention]:
    payload = {"entities": raw}
    return parse_discovery_entities(payload, raw_text=raw_text)


def discover_response_mentions(
    raw_text: str,
    *,
    cache_ttl_s: int = 0,
    track_context: str = "",
) -> tuple[list[ValidatedMention], bool]:
    """Discover validated commercial entities in AI response text.

    Returns ``(entities, live_call)``; cache hits are not billed.
    """
    if not raw_text.strip():
        return [], False

    def _read_cache() -> list[dict[str, Any]] | None:
        return get_mention_discovery_cached(
            raw_text=raw_text,
            ttl_s=cache_ttl_s,
            track_context=track_context,
        )

    cached = _read_cache()
    if cached is not None:
        return _entities_from_cache(cached, raw_text), False

    live_flag = threading.local()

    def _fetch() -> list[dict[str, Any]]:
        messages = [
            {"role": "system", "content": CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM},
            {
                "role": "user",
                "content": citation_response_mention_discovery_user_content(
                    raw_text=raw_text,
                    track_context=track_context,
                ),
            },
        ]
        try:
            text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
            live_flag.did = True
            data = extract_json_object(text)
            if not isinstance(data, dict):
                raise ValueError("mention discovery is not an object")
            entities = parse_discovery_entities(data, raw_text=raw_text)
            cached_entities = _entities_to_cache(entities)
            set_mention_discovery_cached(
                raw_text=raw_text,
                entities=cached_entities,
                ttl_s=cache_ttl_s,
                track_context=track_context,
            )
            return cached_entities
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Mention discovery failed: %s", exc)
            return []

    if cache_ttl_s <= 0:
        return _entities_from_cache(_fetch(), raw_text), True

    digest = mention_discovery_cache_digest(raw_text=raw_text, track_context=track_context)
    try:
        result = run_single_flight(
            digest,
            wait_s=120.0,
            read_cache=_read_cache,
            fetch=_fetch,
            lock_prefix="aperix:mention_discovery:lock:",
        )
        if result is None:
            return [], False
        return _entities_from_cache(result, raw_text), bool(getattr(live_flag, "did", False))
    except SingleFlightWaitTimeout:
        cached = _read_cache()
        if cached is not None:
            return _entities_from_cache(cached, raw_text), False
        logger.warning("Mention discovery single-flight wait timeout")
        return [], False
