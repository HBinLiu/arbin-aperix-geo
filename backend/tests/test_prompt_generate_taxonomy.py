"""Prompt generate taxonomy lock."""

from __future__ import annotations

from aperix_geo.services.prompts.setup import llm_prompt_row_to_internal
from aperix_geo.services.prompts.taxonomy import prompt_taxonomy_lock
from aperix_geo.services.providers.prompts import setup_wizard_prompts_system


def test_prompt_taxonomy_lock_normalizes_values() -> None:
    lock = prompt_taxonomy_lock(
        funnel_stage="BOFU",
        search_intent="transactional",
        decision_type="price_value",
    )
    assert lock.funnel_stage == "bofu"
    assert lock.search_intent == "transactional"
    assert lock.decision_type == "price_value"


def test_llm_prompt_row_to_internal_applies_taxonomy_lock() -> None:
    lock = prompt_taxonomy_lock(
        funnel_stage="tofu",
        search_intent="informational",
        decision_type="category_awareness",
    )
    row = llm_prompt_row_to_internal(
        {
            "text": "红茶怎么选？",
            "funnel": "bofu",
            "intent": "commercial",
            "decision": "solution_comparison",
        },
        taxonomy_lock=lock,
    )
    assert row is not None
    assert row["text"] == "红茶怎么选？"
    assert row["funnel_stage"] == "tofu"
    assert row["search_intent"] == "informational"
    assert row["decision_type"] == "category_awareness"


def test_setup_wizard_prompts_system_includes_taxonomy_lock() -> None:
    system = setup_wizard_prompts_system(
        n=3,
        taxonomy_lock={
            "funnel": "mofu",
            "intent": "commercial",
            "decision": "scenario_fit",
        },
    )
    assert "分类固定" in system
    assert "funnel: mofu" in system
    assert "intent: commercial" in system
    assert "decision: scenario_fit" in system
