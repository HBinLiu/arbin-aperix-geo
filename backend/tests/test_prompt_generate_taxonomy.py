"""Prompt generate taxonomy lock."""

from __future__ import annotations

from aperix_geo.services.prompts.setup import _normalize_generated_prompts
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


def test_normalize_generated_prompts_applies_taxonomy_lock() -> None:
    lock = prompt_taxonomy_lock(
        funnel_stage="tofu",
        search_intent="informational",
        decision_type="category_awareness",
    )
    rows = _normalize_generated_prompts(
        [
            {
                "text": "红茶怎么选？",
                "funnel": "bofu",
                "intent": "commercial",
                "decision": "solution_comparison",
            }
        ],
        limit=1,
        taxonomy_lock=lock,
    )
    assert len(rows) == 1
    assert rows[0]["text"] == "红茶怎么选？"
    assert rows[0]["funnel_stage"] == "tofu"
    assert rows[0]["search_intent"] == "informational"
    assert rows[0]["decision_type"] == "category_awareness"


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
