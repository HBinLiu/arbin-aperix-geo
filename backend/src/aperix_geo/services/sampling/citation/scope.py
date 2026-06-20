"""Closed brand scope for citation page GEO (response-mentioned cross-validated brands)."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.sampling.mentions import CompetitorEntry, collect_match_terms
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def cross_validated_other_brand_labels(response_absa: dict[str, Any]) -> list[str]:
    """Open-set ABSA brand labels (expected already cross-validated in parse analysis)."""
    others = dict(response_absa.get("other_brands_sentiment_absa") or {})
    return [label for label in others if str(label or "").strip()]


def page_geo_brand_scope(
    entity_signals: list[EntitySignalDraft],
    *,
    own_brand: str,
    competitors: list[CompetitorEntry],
    cross_validated_other_brands: list[str] | None = None,
) -> list[str]:
    """Brands to check on citation pages: response-mentioned monitored competitors + cross-validated others."""
    mentioned_labels = {
        draft.entity_label
        for draft in entity_signals
        if draft.mentioned and draft.entity_kind == "competitor"
    }
    scope: list[str] = []
    seen: set[str] = set()
    for entry in competitors:
        if entry.label not in mentioned_labels:
            continue
        name = (entry.brand or entry.label).strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            scope.append(name)
    for label in cross_validated_other_brands or []:
        name = str(label or "").strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            scope.append(name)
    own_mentioned = any(
        draft.mentioned and draft.entity_kind == "own" for draft in entity_signals
    )
    if own_mentioned:
        name = own_brand.strip()
        key = name.lower()
        if name and key not in seen:
            scope.insert(0, name)
    return scope


def page_geo_match_terms_by_brand(
    page_brand_scope: list[str],
    *,
    own_brand: str,
    own_names: list[str],
    competitors: list[CompetitorEntry],
) -> dict[str, list[str]]:
    """Map canonical scope brand names to substring match terms (aliases included)."""
    scope_keys = {name.strip().lower() for name in page_brand_scope if name.strip()}
    terms_by_brand: dict[str, list[str]] = {}
    own_key = own_brand.strip().lower()
    if own_key in scope_keys:
        terms_by_brand[own_brand.strip()] = collect_match_terms(own_brand, *own_names)
    for entry in competitors:
        name = (entry.brand or entry.label).strip()
        if name.lower() in scope_keys:
            terms_by_brand[name] = list(entry.terms) or collect_match_terms(entry.brand, entry.label)
    for name in page_brand_scope:
        key = name.strip().lower()
        if key and name not in terms_by_brand:
            terms_by_brand[name] = collect_match_terms(name)
    return terms_by_brand
