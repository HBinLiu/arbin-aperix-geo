"""Tests for setup prompt generation cache."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from uuid import uuid4

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.prompts import generate_setup_prompts_for_session
from aperix_geo.services.setup.cache.prompts import prompts_generation_hash


def test_prompts_generation_hash_stable_for_topic_order() -> None:
    hash1 = prompts_generation_hash(
        entity="example.com",
        topics=["b", "a"],
        competitors=["rival.com"],
        industry="SaaS",
        keywords="API",
        brief="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    hash2 = prompts_generation_hash(
        entity="example.com",
        topics=["a", "b"],
        competitors=["rival.com"],
        industry="SaaS",
        keywords="API",
        brief="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    assert hash1 == hash2


@patch("aperix_geo.services.setup.prompts.assert_setup_ai_usage_available")
@patch("aperix_geo.services.setup.prompts.update_session")
@patch("aperix_geo.services.setup.prompts.generate_setup_prompts")
@patch("aperix_geo.services.setup.prompts.get_session")
@patch("aperix_geo.services.setup.prompts.require_deepseek_api_key")
def test_generate_setup_prompts_for_session_uses_cache(
    _mock_llm_key,
    mock_get_session,
    mock_generate,
    mock_update_session,
    _mock_assert_ai,
) -> None:
    profile = normalize_niche_profile(
        {
            "company": "Example",
            "industry": "SaaS",
            "keywords": "API",
            "brief": "团队",
        },
        entity="example.com",
    )
    topics = ["AI 可见度"]
    competitors = ["rival.com"]
    prompts_hash = prompts_generation_hash(
        entity="example.com",
        topics=topics,
        competitors=competitors,
        industry="SaaS",
        keywords="API",
        brief="团队",
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
        "subject_type": "domain",
        "profile": profile,
        "competitors": [{"domain": "rival.com", "brand": "Rival", "website_url": "https://rival.com"}],
        "confirmed_competitors_hash": "hash",
        "prompts_hash": prompts_hash,
        "prompts_cache": cached_items,
    }

    items = generate_setup_prompts_for_session(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1",
        session_id="abc123456789",
        topics=topics,
        exclude_prompts=[],
    )

    mock_generate.assert_not_called()
    mock_update_session.assert_called_once()
    assert mock_update_session.call_args.kwargs["patch"]["monitoring_topics"] == topics
    assert items == cached_items


@patch("aperix_geo.services.setup.prompts.assert_setup_ai_usage_available")
@patch("aperix_geo.services.setup.prompts.update_session")
@patch("aperix_geo.services.setup.prompts.generate_setup_prompts")
@patch("aperix_geo.services.setup.prompts.get_session")
@patch("aperix_geo.services.setup.prompts.require_deepseek_api_key")
def test_generate_setup_prompts_for_session_stores_result(
    _mock_llm_key,
    mock_get_session,
    mock_generate,
    mock_update_session,
    _mock_assert_ai,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": "API", "brief": "团队"},
        entity="example.com",
    )
    mock_get_session.return_value = {
        "target": "example.com",
        "subject_type": "domain",
        "profile": profile,
        "competitors": [{"domain": "rival.com", "brand": "Rival", "website_url": ""}],
        "confirmed_competitors_hash": "hash",
    }
    generated = [
        {"topic": "支付", "prompts": [{"text": "Q1", "funnel_stage": "tofu", "search_intent": "informational"}]}
    ]
    mock_generate.return_value = generated

    items = generate_setup_prompts_for_session(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1",
        session_id="abc123456789",
        topics=["支付"],
        exclude_prompts=[],
    )

    assert items == generated
    mock_generate.assert_called_once()
    mock_update_session.assert_called_once()
    patch = mock_update_session.call_args.kwargs["patch"]
    assert patch["monitoring_topics"] == ["支付"]
    assert patch["prompts_cache"] == generated
    assert patch["prompts_hash"]
