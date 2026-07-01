"""Tests for setup discover orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.cache.competitors import (
    cached_competitors_result,
    competitors_search_hash,
)
from aperix_geo.services.setup.cache.profile import profile_hash
from aperix_geo.services.setup.discover import discover_setup
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError


def test_competitors_search_hash_stable_for_keyword_order() -> None:
    hash1 = competitors_search_hash(
        subject_type="domain",
        target="example.com",
        search_queries=["b", "a"],
    )
    hash2 = competitors_search_hash(
        subject_type="domain",
        target="example.com",
        search_queries=["a", "b"],
    )
    assert hash1 == hash2


def test_cached_competitors_result_requires_items() -> None:
    competitors_hash = competitors_search_hash(
        subject_type="domain",
        target="example.com",
        search_queries=["kw"],
    )
    assert cached_competitors_result({}, competitors_hash=competitors_hash) is None
    assert cached_competitors_result(
        {
            "competitors_hash": competitors_hash,
            "competitors": [],
        },
        competitors_hash=competitors_hash,
    ) is None
    cached = cached_competitors_result(
        {
            "competitors_hash": competitors_hash,
            "competitors": [{"domain": "rival.com", "brand": "Rival"}],
        },
        competitors_hash=competitors_hash,
    )
    assert cached is not None
    assert cached["competitors"][0]["brand"] == "Rival"


@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_discover_brand_without_materials_raises(_mock_llm_key, _mock_unique) -> None:
    with pytest.raises(MaterialsInsufficientError):
        discover_setup(
            db=MagicMock(),
            tenant_id=uuid4(),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            subject_type="brand",
            domain=None,
            brand="深睿医疗",
            region="CN",
            language="zh-CN",
        )


@patch("aperix_geo.services.setup.discover._fetch_homepage_inputs", return_value=("", ()))
@patch("aperix_geo.services.setup.discover.discover_competitors_for_session")
@patch("aperix_geo.services.setup.discover.get_session")
@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_discover_setup_reuses_session_and_competitor_cache(
    _mock_llm_key,
    _mock_unique,
    mock_get_session,
    mock_discover,
    _mock_fetch_homepage,
) -> None:
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": ["AI SaaS"]},
        entity="example.com",
    )
    profile_hash_value = profile_hash(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
    )
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "region": "CN",
        "language": "zh-CN",
        "profile_hash": profile_hash_value,
        "profile": profile,
        "search_queries": ["AI SaaS"],
        "competitors": [{"domain": "rival.com", "brand": "Rival", "website_url": "https://rival.com"}],
    }
    mock_discover.return_value = [{"domain": "rival.com", "brand": "Rival", "website_url": "https://rival.com"}]

    result = discover_setup(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_type="domain",
        domain="example.com",
        brand=None,
        region="CN",
        language="zh-CN",
        session_id="abc123",
    )

    assert result["session_id"] == "abc123"
    assert result["competitors"][0]["domain"] == "rival.com"
    mock_discover.assert_called_once()
