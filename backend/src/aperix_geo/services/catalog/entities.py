"""Cached analysis entity catalog."""

from __future__ import annotations

from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.metrics import build_analysis_entities
from aperix_geo.services.catalog.cache import entities_cache_get, entities_cache_set


def get_analysis_entities(subject: Subject) -> dict[str, Any]:
    """Return entity catalog for FilterBar; Redis-backed with L1."""
    cached = entities_cache_get(subject.id)
    if cached is not None:
        return cached

    payload = build_analysis_entities(subject)
    entities_cache_set(subject.id, payload)
    return payload
