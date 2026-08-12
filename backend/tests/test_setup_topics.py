"""Tests for setup topics step (competitors → keywords topics + fallback summary)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.topics import confirmed_competitors_hash, run_setup_topics_step


def test_confirmed_competitors_hash_order_independent() -> None:
    a = [{"domain": "b.com", "brand": "B", "website_url": ""}]
    b = [{"domain": "a.com", "brand": "A", "website_url": ""}, {"domain": "b.com", "brand": "B", "website_url": ""}]
    c = [{"domain": "b.com", "brand": "B", "website_url": ""}, {"domain": "a.com", "brand": "A", "website_url": ""}]
    assert confirmed_competitors_hash(b) == confirmed_competitors_hash(c)
    assert confirmed_competitors_hash(a) != confirmed_competitors_hash(b)


@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.get_session")
def test_run_setup_topics_step_uses_keywords_and_fallback_summary(
    mock_get_session,
    mock_summary,
    mock_update,
    mock_enrich,
) -> None:
    profile = normalize_niche_profile(
        {
            "industry": "SaaS",
            "keywords": ["AI可见度监测", "竞品对比"],
            "company": "Example",
            "brief": "市场团队",
        },
        entity="example.com",
    )
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "monitoring_topics": ["AI可见度监测", "竞品对比"],
    }
    mock_summary.return_value = ("# Example\n\n## 概述\n测试", {})
    mock_enrich.side_effect = lambda items, *, session=None: items
    mock_update.return_value = True

    competitors = [CompetitorItem(domain="rival.com", brand="Rival", website_url="https://rival.com")]
    topics = run_setup_topics_step(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1",
        session_id="abc123456789",
        competitors=competitors,
    )

    assert topics == [
        {"name": "AI可见度监测"},
        {"name": "竞品对比"},
    ]
    mock_summary.assert_called_once()
    patch = mock_update.call_args.kwargs["patch"]
    assert patch["profile_summary"].startswith("# Example")
    assert patch["competitors"][0]["domain"] == "rival.com"
    assert patch["monitoring_topics"] == ["AI可见度监测", "竞品对比"]
