"""Prompt taxonomy helpers."""

from __future__ import annotations

import pytest

from aperix_geo.services.prompts.taxonomy import (
    normalize_funnel_stage,
    normalize_search_intent,
    prompt_taxonomy_meta,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("tofu", "tofu"),
        ("BOFU", "bofu"),
        ("invalid", "mofu"),
        (None, "mofu"),
    ],
)
def test_normalize_funnel_stage(raw: str | None, expected: str) -> None:
    assert normalize_funnel_stage(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("informational", "informational"),
        ("transactional", "transactional"),
        ("navigational", "commercial"),
        ("", "commercial"),
    ],
)
def test_normalize_search_intent(raw: str | None, expected: str) -> None:
    assert normalize_search_intent(raw) == expected


def test_prompt_taxonomy_meta() -> None:
    meta = prompt_taxonomy_meta()
    assert meta.default_funnel_stage == "mofu"
    assert meta.default_search_intent == "commercial"
    assert meta.default_decision_type == "category_awareness"
    assert {item.value for item in meta.funnel_stages} == {"tofu", "mofu", "bofu"}
    funnel_labels = {item.value: item.label for item in meta.funnel_stages}
    assert funnel_labels["tofu"] == "认知期"
    assert {item.value for item in meta.search_intents} == {
        "informational",
        "commercial",
        "transactional",
    }
    intent_labels = {item.value: item.label for item in meta.search_intents}
    assert intent_labels["informational"] == "了解型"
    assert {item.value for item in meta.decision_types} == {
        "category_awareness",
        "price_value",
        "scenario_fit",
        "solution_comparison",
        "trust_risk",
    }
    decision_labels = {item.value: item.label for item in meta.decision_types}
    assert decision_labels["category_awareness"] == "品类认知"
