"""Cached analysis entity catalog."""

from __future__ import annotations

from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.metrics import build_analysis_entities
from aperix_geo.services.catalog.cache import entities_cache_get, entities_cache_set


def _normalize_entity_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    legacy = (item.pop("display_name", None) or "").strip()
    label = (item.get("label") or "").strip()
    brand = (item.get("brand") or "").strip()
    if not brand and legacy and legacy.casefold() != label.casefold():
        item["brand"] = legacy
    elif not brand:
        item["brand"] = None
    return item


def _normalize_entities_payload(payload: dict[str, Any]) -> dict[str, Any]:
    entities = payload.get("entities") or []
    if not isinstance(entities, list):
        return {"entities": []}
    return {"entities": [_normalize_entity_row(row) for row in entities if isinstance(row, dict)]}


def get_analysis_entities(subject: Subject) -> dict[str, Any]:
    """Return entity catalog for FilterBar; Redis-backed with L1."""
    cached = entities_cache_get(subject.id)
    if cached is not None:
        return _normalize_entities_payload(cached)

    payload = build_analysis_entities(subject)
    entities_cache_set(subject.id, payload)
    return payload
