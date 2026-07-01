"""Tests for setup topics step (confirmed competitors → summary + topics)."""

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


@patch("aperix_geo.services.setup.topics.consume_ai_usage")
@patch("aperix_geo.services.setup.topics.assert_ai_usage_available")
@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_topic_generation_stage")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.get_session")
@patch("aperix_geo.services.setup.topics.require_deepseek_api_key")
def test_run_setup_topics_step_generates_summary_and_topics(
    _mock_llm_key,
    mock_get_session,
    mock_summary,
    mock_topics,
    mock_update,
    mock_enrich,
    _mock_assert_ai,
    _mock_consume,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": ["AI SaaS"], "company": "Example"},
        entity="example.com",
    )
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "research_payload": {"mode": "domain", "target": "example.com", "site_data": {}},
    }
    mock_summary.return_value = ("# Example\n\n## 概述\n测试", {})
    clusters = [
        {"name": "AI 可见度监测", "seed_queries": []},
        {"name": "竞品对比", "seed_queries": []},
    ]
    mock_topics.return_value = (clusters, [], {})
    call_order: list[str] = []

    def _topics_side_effect(*_args, **_kwargs):
        call_order.append("topics")
        return clusters, [], {}

    def _summary_side_effect(*_args, **_kwargs):
        call_order.append("summary")
        return "# Example\n\n## 概述\n测试", {}

    mock_topics.side_effect = _topics_side_effect
    mock_summary.side_effect = _summary_side_effect
    mock_enrich.side_effect = lambda items, *, session=None: items

    competitors = [CompetitorItem(domain="rival.com", brand="Rival", website_url="https://rival.com")]
    topics = run_setup_topics_step(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1",
        session_id="abc123456789",
        competitors=competitors,
    )

    assert topics == [
        {"name": "AI 可见度监测"},
        {"name": "竞品对比"},
    ]
    assert call_order == ["topics", "summary"]
    summary_competitors = mock_summary.call_args.kwargs["competitors"]
    assert summary_competitors[0]["domain"] == "rival.com"
    patch = mock_update.call_args.kwargs["patch"]
    assert patch["profile_summary"].startswith("# Example")
    assert patch["competitors"][0]["domain"] == "rival.com"
    assert "topic_clusters" in patch


@patch("aperix_geo.services.setup.topics.consume_ai_usage")
@patch("aperix_geo.services.setup.topics.assert_ai_usage_available")
@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_topic_generation_stage")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.get_session")
@patch("aperix_geo.services.setup.topics.require_deepseek_api_key")
def test_run_setup_topics_step_preserves_competitor_aliases(
    _mock_llm_key,
    mock_get_session,
    mock_summary,
    mock_topics,
    mock_update,
    mock_enrich,
    _mock_assert_ai,
    _mock_consume,
) -> None:
    profile = normalize_niche_profile({"industry": "SaaS", "company": "Example"}, entity="example.com")
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
    }
    mock_summary.return_value = ("# Example", {})
    mock_topics.return_value = (
        [{"name": "主题 A", "seed_queries": []}],
        [],
        {},
    )
    mock_enrich.side_effect = lambda items, *, session=None: items

    competitors = [
        CompetitorItem(
            domain="wise.com",
            brand="Wise",
            website_url="https://wise.com",
            aliases=["TransferWise"],
        )
    ]
    run_setup_topics_step(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1", session_id="abc123456789", competitors=competitors)

    summary_competitors = mock_summary.call_args.kwargs["competitors"]
    assert summary_competitors[0]["aliases"] == ["TransferWise"]


@patch("aperix_geo.services.setup.topics.consume_ai_usage")
@patch("aperix_geo.services.setup.topics.assert_ai_usage_available")
@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_topic_generation_stage")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.get_session")
@patch("aperix_geo.services.setup.topics.require_deepseek_api_key")
def test_run_setup_topics_step_regenerates_topics_when_competitors_change(
    _mock_llm_key,
    mock_get_session,
    mock_summary,
    mock_topics,
    mock_update,
    mock_enrich,
    _mock_assert_ai,
    _mock_consume,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": ["AI SaaS"], "company": "Example"},
        entity="example.com",
    )
    existing = ["AI 可见度监测"]
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "monitoring_topics": existing,
        "profile_summary": "# Example\n\n旧摘要",
        "confirmed_competitors_hash": "old-hash",
    }
    mock_summary.return_value = ("# Example\n\n新摘要", {})
    mock_topics.return_value = (
        [
            {"name": "新主题 A", "seed_queries": []},
            {"name": "新主题 B", "seed_queries": []},
        ],
        [],
        {},
    )
    mock_enrich.side_effect = lambda items, *, session=None: items

    competitors = [CompetitorItem(domain="new-rival.com", brand="New Rival", website_url="https://new-rival.com")]
    topics = run_setup_topics_step(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id="user-1",
        session_id="abc123456789",
        competitors=competitors,
    )

    assert topics == [
        {"name": "新主题 A"},
        {"name": "新主题 B"},
    ]
    mock_summary.assert_called_once()
    mock_topics.assert_called_once()
    patch = mock_update.call_args.kwargs["patch"]
    assert patch["monitoring_topics"] == ["新主题 A", "新主题 B"]
    assert patch["prompts_hash"] is None
    assert patch["prompts_cache"] is None


@patch("aperix_geo.services.setup.topics.consume_ai_usage")
@patch("aperix_geo.services.setup.topics.assert_ai_usage_available")
@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.get_session")
@patch("aperix_geo.services.setup.topics.require_deepseek_api_key")
def test_run_setup_topics_step_summary_after_research_payload_cleared(
    _mock_llm_key,
    mock_get_session,
    mock_summary,
    mock_update,
    mock_enrich,
    _mock_assert_ai,
    _mock_consume,
) -> None:
    """topics 清除 research_payload 后，摘要仍能从 session 字段正确生成。"""
    profile = normalize_niche_profile(
        {"industry": "SaaS", "company": "Example"},
        entity="example.com",
    )
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "monitoring_topics": ["已有主题"],
        "topic_clusters": [
            {
                "name": "已有主题",
                "seed_queries": [
                    {
                        "text": "已有主题相关问句示例一",
                        "intent": "commercial",
                        "funnel": "mofu",
                        "decision_type": "scenario_fit",
                    }
                ]
                * 3,
            }
        ],
        "profile_summary": "",
        "confirmed_competitors_hash": "same-hash",
    }
    mock_summary.return_value = ("# Example\n\n新摘要", {})
    mock_enrich.side_effect = lambda items, *, session=None: items

    competitors = [CompetitorItem(domain="rival.com", brand="Rival", website_url="https://rival.com")]
    with patch(
        "aperix_geo.services.setup.topics.confirmed_competitors_hash",
        return_value="same-hash",
    ):
        topics = run_setup_topics_step(
            db=MagicMock(),
            tenant_id=uuid4(),
            user_id="user-1",
            session_id="abc123456789",
            competitors=competitors,
        )

    assert topics == [{"name": "已有主题"}]
    assert mock_summary.call_args is not None
    kwargs = mock_summary.call_args.kwargs
    assert kwargs["subject_type"] == "domain"
    assert kwargs["target"] == "example.com"
    assert kwargs["region"] == "CN"
    session_patch = mock_update.call_args.kwargs["patch"]
    assert session_patch["competitors"][0]["domain"] == "rival.com"


@patch("aperix_geo.services.setup.topics.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.topics.update_session")
@patch("aperix_geo.services.setup.topics.run_profile_summary_stage")
@patch("aperix_geo.services.setup.topics.run_topic_generation_stage")
@patch("aperix_geo.services.setup.topics.get_session")
@patch("aperix_geo.services.setup.topics.require_deepseek_api_key")
def test_run_setup_topics_step_always_persists_confirmed_competitors(
    _mock_llm_key,
    mock_get_session,
    _mock_topics,
    mock_summary,
    mock_update,
    mock_enrich,
) -> None:
    """竞品 hash 未变时仍须把 enrich 后的列表写回 session.competitors。"""
    profile = normalize_niche_profile({"industry": "SaaS", "company": "Example"}, entity="example.com")
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "monitoring_topics": ["已有主题"],
        "topic_clusters": [
            {
                "name": "已有主题",
                "seed_queries": [
                    {
                        "text": "已有主题相关问句示例一",
                        "intent": "commercial",
                        "funnel": "mofu",
                        "decision_type": "scenario_fit",
                    }
                ]
                * 3,
            }
        ],
        "profile_summary": "# Example",
        "confirmed_competitors_hash": "stable-hash",
    }
    mock_enrich.return_value = [
        {
            "domain": "rival.com",
            "website_url": "https://rival.com",
            "brand": "Rival",
            "summary": "竞品摘要",
            "aliases": ["Rival Pay"],
        }
    ]
    with patch(
        "aperix_geo.services.setup.topics.confirmed_competitors_hash",
        return_value="stable-hash",
    ):
        run_setup_topics_step(
            db=MagicMock(),
            tenant_id=uuid4(),
            user_id="user-1",
            session_id="abc123456789",
            competitors=[CompetitorItem(domain="rival.com", brand="Rival", website_url="https://rival.com")],
        )

    mock_summary.assert_not_called()
    session_patch = mock_update.call_args.kwargs["patch"]
    assert session_patch["competitors"][0]["summary"] == "竞品摘要"
    assert session_patch["competitors"][0]["aliases"] == ["Rival Pay"]
