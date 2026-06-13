"""Tests for setup prompt generation cache."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.cache.prompts import (
    generate_setup_prompts_for_session,
    prompts_generation_fingerprint,
)


def test_prompts_fingerprint_stable_for_topic_order() -> None:
    fp1 = prompts_generation_fingerprint(
        entity="example.com",
        topics=["b", "a"],
        competitors=["rival.com"],
        industry="SaaS",
        core_features="API",
        target_customers="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    fp2 = prompts_generation_fingerprint(
        entity="example.com",
        topics=["a", "b"],
        competitors=["rival.com"],
        industry="SaaS",
        core_features="API",
        target_customers="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    assert fp1 == fp2


@patch("aperix_geo.services.setup.cache.prompts.update_session")
@patch("aperix_geo.services.setup.cache.prompts.generate_setup_prompts")
@patch("aperix_geo.services.setup.cache.prompts.get_session")
def test_generate_setup_prompts_for_session_uses_cache(
    mock_get_session,
    mock_generate,
    mock_update_session,
) -> None:
    profile = normalize_niche_profile(
        {
            "company": "Example",
            "industry": "SaaS",
            "core_features": "API",
            "target_customers": "团队",
        },
        entity="example.com",
    )
    topics = ["AI 可见度"]
    competitors = ["rival.com"]
    fp = prompts_generation_fingerprint(
        entity="example.com",
        topics=topics,
        competitors=competitors,
        industry="SaaS",
        core_features="API",
        target_customers="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    cached_items = [
        {
            "topic": "AI 可见度",
            "prompts": [{"text": "问句1", "funnel_stage": "tofu", "search_intent": "informational"}],
        }
    ]
    mock_get_session.return_value = {
        "target": "example.com",
        "profile": profile,
        "prompts_fingerprint": fp,
        "prompts_cache": cached_items,
    }

    items = generate_setup_prompts_for_session(
        user_id="user-1",
        session_id="abc123456789",
        topics=topics,
        competitors=competitors,
        exclude_prompts=[],
    )

    mock_generate.assert_not_called()
    mock_update_session.assert_not_called()
    assert items == cached_items


@patch("aperix_geo.services.setup.cache.prompts.update_session")
@patch("aperix_geo.services.setup.cache.prompts.generate_setup_prompts")
@patch("aperix_geo.services.setup.cache.prompts.get_session")
def test_generate_setup_prompts_for_session_stores_result(
    mock_get_session,
    mock_generate,
    mock_update_session,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "core_features": "API", "target_customers": "团队"},
        entity="example.com",
    )
    mock_get_session.return_value = {"target": "example.com", "profile": profile}
    generated = [
        {"topic": "支付", "prompts": [{"text": "Q1", "funnel_stage": "tofu", "search_intent": "informational"}]}
    ]
    mock_generate.return_value = generated

    items = generate_setup_prompts_for_session(
        user_id="user-1",
        session_id="abc123456789",
        topics=["支付"],
        competitors=[],
        exclude_prompts=[],
    )

    assert items == generated
    mock_generate.assert_called_once()
    mock_update_session.assert_called_once()
    patch = mock_update_session.call_args.kwargs["patch"]
    assert patch["prompts_cache"] == generated
    assert patch["prompts_fingerprint"]
