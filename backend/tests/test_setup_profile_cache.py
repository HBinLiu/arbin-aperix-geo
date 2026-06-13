"""Tests for setup Step1 profile cache."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.discover import discover_profile
from aperix_geo.services.setup.cache.profile import profile_fingerprint


def test_profile_fingerprint_includes_website_url() -> None:
    fp1 = profile_fingerprint(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="https://www.example.com",
    )
    fp2 = profile_fingerprint(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
    )
    assert fp1 != fp2


@patch("aperix_geo.services.setup.discover.create_session")
@patch("aperix_geo.services.setup.discover.set_profile_cache")
@patch("aperix_geo.services.setup.discover.get_profile_cache")
@patch("aperix_geo.services.setup.discover.build_subject_profile")
@patch("aperix_geo.services.setup.discover._require_llm_key")
def test_discover_profile_uses_cache(
    _mock_llm_key,
    mock_build,
    mock_get_cache,
    mock_set_cache,
    mock_create_session,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "micro_keywords": ["AI SaaS"]},
        entity="example.com",
    )
    mock_get_cache.return_value = {
        "profile": dict(profile),
        "monitoring_topics": ["topic-a"],
        "research_payload": {"mode": "domain", "target": "example.com", "site_data": {}},
    }
    mock_create_session.return_value = "abc123"

    result = discover_profile(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_type="domain",
        domain="example.com",
        brand=None,
        region="CN",
        language="zh-CN",
    )

    mock_build.assert_not_called()
    mock_set_cache.assert_not_called()
    assert result["session_id"] == "abc123"
    assert result["monitoring_topics"] == ["topic-a"]
