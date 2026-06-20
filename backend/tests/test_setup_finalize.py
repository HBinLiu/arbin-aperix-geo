"""Tests for setup helpers and finalize."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.schemas.catalog import CompetitorItem, SetupFinalizeBody, SetupPromptItem, SetupTopicItem
from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.helpers import (
    subject_aliases_from_session,
    subject_summary_from_session,
    validate_confirmed_competitors,
)
from aperix_geo.services.setup.finalize import finalize_setup


def test_validate_confirmed_competitors_domain_mode() -> None:
    validate_confirmed_competitors(
        subject_type="domain",
        competitors=[CompetitorItem(domain="rival.com", brand="Rival", website_url="https://rival.com")],
    )


def test_subject_aliases_from_session_includes_company_when_different() -> None:
    profile = normalize_niche_profile({"company": "Airwallex"}, entity="airwallex.com")
    aliases = subject_aliases_from_session(
        {
            "target": "airwallex.com",
            "profile": profile,
        }
    )
    assert aliases == ["Airwallex"]


def test_subject_summary_from_session_uses_research_site_data() -> None:
    summary = subject_summary_from_session(
        {
            "research_payload": {
                "mode": "domain",
                "site_data": {
                    "title": "Airwallex",
                    "description": "全球跨境支付平台",
                },
            },
        }
    )
    assert summary == "全球跨境支付平台"


@patch("aperix_geo.services.setup.finalize.subject_summary_from_session", return_value="全球跨境支付")
@patch("aperix_geo.services.competitor.enrich.enrich_confirmed_competitors")
@patch("aperix_geo.services.setup.finalize.delete_session")
@patch("aperix_geo.services.setup.finalize.create_and_enqueue_sampling_job")
@patch("aperix_geo.services.setup.finalize.resolve_subject_sampling_platforms")
@patch("aperix_geo.services.setup.finalize.get_session")
def test_finalize_setup_writes_aliases_and_deletes_session(
    mock_get_session,
    mock_platforms,
    mock_enqueue,
    mock_delete,
    mock_enrich,
    mock_subject_summary,
) -> None:
    profile = normalize_niche_profile({"company": "Airwallex"}, entity="airwallex.com")
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "airwallex.com",
        "domain": "airwallex.com",
        "website_url": "https://airwallex.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "profile_summary": "# Airwallex",
        "competitors_hash": "discover-hash",
        "competitors": [
            {
                "domain": "wise.com",
                "website_url": "https://wise.com",
                "brand": "Wise",
                "summary": "",
                "aliases": [],
            }
        ],
        "confirmed_competitors_hash": "confirmed-hash",
    }
    mock_platforms.return_value = ["openai"]
    mock_enqueue.return_value = MagicMock(id="job-1")
    mock_enrich.side_effect = lambda items, *, session=None: items

    db = MagicMock()
    user = MagicMock(tenant_id="tenant-1", id="user-1")
    body = SetupFinalizeBody(
        session_id="abc123456789",
        topics=[
            SetupTopicItem(
                name="跨境支付",
                prompts=[SetupPromptItem(text="哪家跨境支付更好？", funnel_stage="mofu", search_intent="commercial")],
            )
        ],
    )

    subject, job = finalize_setup(db, user=user, session_id=body.session_id, body=body)

    assert subject.aliases == ["Airwallex"]
    assert subject.brand == "Airwallex"
    assert subject.summary == "全球跨境支付"
    mock_delete.assert_called_once_with(user_id="user-1", session_id=body.session_id)
    assert job.id == "job-1"
