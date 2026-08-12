"""Tests for setup discover orchestration (async enqueue + session reuse)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.cache.profile import profile_hash
from aperix_geo.services.setup.discover import start_discover_setup, run_discover_setup_job
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError


@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_discover_brand_without_materials_raises(_mock_llm_key, _mock_unique) -> None:
    with pytest.raises(MaterialsInsufficientError):
        start_discover_setup(
            db=MagicMock(),
            tenant_id=uuid4(),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            subject_type="brand",
            domain=None,
            brand="深睿医疗",
            region="CN",
            language="zh-CN",
        )


@patch("aperix_geo.services.setup.discover.set_discover_job")
@patch("aperix_geo.services.setup.discover.update_session", return_value=True)
@patch("aperix_geo.services.setup.discover.get_session")
@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_start_discover_setup_reuses_session_ready(
    _mock_llm_key,
    _mock_unique,
    mock_get_session,
    mock_update,
    mock_set_job,
) -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测 SaaS",
            "keywords": [
                "AI可见度监测",
                "品牌搜索可见度",
                "多平台GEO监测",
            ],
            "brief": "市场团队",
        },
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
    }

    result = start_discover_setup(
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
    assert result["status"] == "ready"
    mock_update.assert_called()
    mock_set_job.assert_called()
    assert mock_set_job.call_args.kwargs["status"] == "ready"


@patch("aperix_geo.tasks.setup.setup_discover_profile")
@patch("aperix_geo.services.setup.discover.assert_setup_ai_usage_available")
@patch("aperix_geo.services.setup.discover.find_active_discover_session", return_value=None)
@patch("aperix_geo.services.setup.discover.get_profile_cache", return_value=None)
@patch("aperix_geo.services.setup.discover.set_discover_job")
@patch("aperix_geo.services.setup.discover.create_session", return_value="newsession")
@patch("aperix_geo.services.setup.discover.get_session", return_value=None)
@patch("aperix_geo.services.subject.duplicate.assert_tenant_subject_unique")
@patch("aperix_geo.services.setup.discover.require_deepseek_api_key")
def test_start_discover_setup_enqueues_celery(
    _mock_llm_key,
    _mock_unique,
    _mock_get_session,
    mock_create,
    mock_set_job,
    _mock_cache,
    _mock_active,
    _mock_quota,
    mock_task,
) -> None:
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

    assert result["session_id"] == "newsession"
    assert result["status"] == "pending"
    mock_create.assert_called_once()
    mock_set_job.assert_called()
    assert mock_set_job.call_args.kwargs["status"] == "pending"
    mock_task.delay.assert_called_once()


@patch("aperix_geo.services.setup.discover.set_discover_job")
@patch("aperix_geo.services.setup.discover._apply_profile_to_session")
@patch("aperix_geo.services.setup.discover._load_or_build_profile")
@patch("aperix_geo.services.setup.discover._prepare_profile_inputs")
@patch("aperix_geo.services.setup.discover.get_session")
@patch("aperix_geo.services.setup.discover.SessionLocal")
def test_run_discover_setup_job_marks_ready(
    mock_session_local,
    mock_get_session,
    mock_prepare,
    mock_load,
    mock_apply,
    mock_set_job,
) -> None:
    mock_session_local.return_value = MagicMock()
    mock_get_session.return_value = {
        "subject_type": "domain",
        "target": "example.com",
        "materials_saved": False,
    }
    profile = normalize_niche_profile(
        {"industry": "SaaS", "keywords": ["GEO"], "brief": "团队"},
        entity="example.com",
    )
    mock_prepare.return_value = MagicMock(website_url="https://example.com")
    mock_load.return_value = (profile, {"ok": True}, False)

    run_discover_setup_job(
        user_id="u1",
        tenant_id=uuid4(),
        session_id="sid1",
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
        profile_hash="abc",
    )

    mock_apply.assert_called_once()
    statuses = [c.kwargs["status"] for c in mock_set_job.call_args_list]
    assert "running" in statuses
    assert statuses[-1] == "ready"
