"""Tests for setup Step1 profile cache."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.cache.profile import profile_hash
from aperix_geo.services.setup.discover import start_discover_setup


def test_profile_hash_includes_website_url() -> None:
    fp1 = profile_hash(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="https://www.example.com",
    )
    fp2 = profile_hash(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
    )
    assert fp1 != fp2


@patch("aperix_geo.services.setup.discover.set_discover_job")
@patch("aperix_geo.services.setup.discover._apply_profile_to_session")
@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.create_session")
@patch("aperix_geo.services.setup.discover.set_profile_cache")
@patch("aperix_geo.services.setup.discover.get_profile_cache")
@patch("aperix_geo.services.setup.discover.run_niche_profile_stage")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_start_discover_setup_uses_profile_cache(
    _mock_llm_key,
    mock_niche,
    mock_get_cache,
    mock_set_cache,
    mock_create_session,
    _mock_unique,
    mock_apply,
    mock_set_job,
) -> None:
    profile = normalize_niche_profile(
        {
            "industry": "SaaS",
            "keywords": [
                "AI 可见度监测",
                "品牌搜索可见度",
                "多平台GEO监测",
                "品牌引用分析",
                "GEO品牌监测",
            ],
            "brief": "市场团队",
        },
        entity="example.com",
    )
    mock_get_cache.return_value = {
        "profile": dict(profile),
        "research_payload": {"mode": "domain", "target": "example.com", "site_data": {}},
    }
    mock_create_session.return_value = "abc123"

    result = start_discover_setup(
        db=MagicMock(),
        tenant_id=uuid4(),
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_type="domain",
        domain="example.com",
        brand=None,
        region="CN",
        language="zh-CN",
    )

    mock_niche.assert_not_called()
    mock_set_cache.assert_not_called()
    mock_apply.assert_called_once()
    mock_set_job.assert_called()
    assert mock_set_job.call_args.kwargs["status"] == "ready"
    assert result["session_id"] == "abc123"
    assert result["status"] == "ready"
