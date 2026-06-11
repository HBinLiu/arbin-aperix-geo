"""Prompt funnel stage and search intent taxonomy."""

from __future__ import annotations

FUNNEL_STAGES = frozenset({"tofu", "mofu", "bofu"})
SEARCH_INTENTS = frozenset({"informational", "commercial", "transactional"})

DEFAULT_FUNNEL_STAGE = "mofu"
DEFAULT_SEARCH_INTENT = "commercial"


def normalize_funnel_stage(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in FUNNEL_STAGES else DEFAULT_FUNNEL_STAGE


def normalize_search_intent(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in SEARCH_INTENTS else DEFAULT_SEARCH_INTENT
