"""Tests for setup discover orchestration."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.cache.competitors import (
    cached_competitors_result,
    competitors_search_fingerprint,
)
from aperix_geo.services.setup.discover import discover_competitors_from_session


def test_competitors_fingerprint_stable_for_keyword_order() -> None:
    fp1 = competitors_search_fingerprint(
        subject_type="domain",
        target="example.com",
        micro_keywords=["b", "a"],
    )
    fp2 = competitors_search_fingerprint(
        subject_type="domain",
        target="example.com",
        micro_keywords=["a", "b"],
    )
    assert fp1 == fp2


def test_cached_competitors_result_requires_summary_and_items() -> None:
    fp = competitors_search_fingerprint(
        subject_type="domain",
        target="example.com",
        micro_keywords=["kw"],
    )
    assert cached_competitors_result({}, fingerprint=fp) is None
    assert cached_competitors_result(
        {
            "competitors_fingerprint": fp,
            "competitors_cache": [],
            "profile_summary": "summary",
        },
        fingerprint=fp,
    ) is None
    cached = cached_competitors_result(
        {
            "competitors_fingerprint": fp,
            "competitors_cache": [{"domain": "rival.com", "brand": "Rival"}],
            "profile_summary": "# Summary",
        },
        fingerprint=fp,
    )
    assert cached is not None
    assert cached["competitors"][0]["brand"] == "Rival"


@patch("aperix_geo.services.setup.discover.update_session")
@patch("aperix_geo.services.setup.discover.get_session")
@patch("aperix_geo.services.setup.discover._require_llm_key")
def test_discover_competitors_uses_cache_when_fingerprint_matches(
    _mock_llm_key,
    mock_get_session,
    mock_update_session,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "micro_keywords": ["AI SaaS"]},
        entity="example.com",
    )
    fp = competitors_search_fingerprint(
        subject_type="domain",
        target="example.com",
        micro_keywords=["AI SaaS"],
    )
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile": profile,
        "micro_keywords": ["AI SaaS"],
        "monitoring_topics": ["topic-a"],
        "competitors_fingerprint": fp,
        "competitors_cache": [{"domain": "rival.com", "brand": "Rival", "summary": "x"}],
        "profile_summary": "# Example",
    }

    with patch("aperix_geo.services.setup.discover.search_domain_competitors") as mock_search:
        result = discover_competitors_from_session(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            session_id="abc123",
            monitoring_topics=["topic-b"],
        )

    mock_search.assert_not_called()
    assert result["competitors"][0]["domain"] == "rival.com"
    mock_update_session.assert_called_once()
