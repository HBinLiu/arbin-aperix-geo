"""Tests for Setup LLM stages and payloads."""

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.llm.payloads import (
    build_monitoring_topics_payload,
    build_profile_summary_payload,
)
from aperix_geo.services.setup.llm.stages import (
    run_monitoring_topics_stage,
    run_niche_profile_stage,
    run_profile_summary_stage,
)


def test_build_monitoring_topics_payload_includes_profile() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测 SaaS",
            "features": ["AI 可见度"],
            "customers": "市场团队",
            "keywords": ["AI 品牌可见度监测 SaaS"],
        },
        entity="sheepgeo.com",
    )
    payload = build_monitoring_topics_payload(
        subject_type="domain",
        target="sheepgeo.com",
        profile=profile,
    )
    assert payload == {
        "subject_type": "domain",
        "target": "sheepgeo.com",
        "niche_profile": {
            "company": "sheepgeo.com",
            "industry": "GEO 监测 SaaS",
            "customers": "市场团队",
            "keywords": "AI 品牌可见度监测 SaaS",
        },
    }
    assert "features" not in payload["niche_profile"]


def test_build_profile_summary_payload_uses_session_fields() -> None:
    profile = normalize_niche_profile(
        {"industry": "GEO 监测 SaaS", "company": "SheepGeo"},
        entity="sheepgeo.com",
    )
    payload = build_profile_summary_payload(
        subject_type="domain",
        target="sheepgeo.com",
        region="CN",
        language="zh-CN",
        profile=profile,
        competitors=[{"domain": "rival.com", "brand": "Rival", "summary": "同业竞品"}],
    )
    assert payload["subject_type"] == "domain"
    assert payload["target"] == "sheepgeo.com"
    assert payload["region"] == "中国大陆"
    assert payload["language"] == "简体中文"
    assert payload["niche_profile"]["company"] == "SheepGeo"
    assert payload["competitors"][0]["brand"] == "Rival"
    assert "site_data" not in payload
    assert "web_research" not in payload


@patch("aperix_geo.services.setup.llm.stages.generate_niche_profile_via_llm")
@patch("aperix_geo.services.setup.llm.payloads.build_subject_research_payload")
def test_run_niche_profile_stage(mock_payload, mock_llm) -> None:
    mock_payload.return_value = {"mode": "domain", "target": "example.com"}
    mock_llm.return_value = (
        {
            "company": "Example",
            "industry": "跨境 B2B 支付",
            "features": ["收款"],
            "customers": "卖家",
            "keywords": ["SMB 跨境收款 SaaS"],
        },
        {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    profile, research, usage = run_niche_profile_stage(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
    )

    assert profile["industry"] == "跨境 B2B 支付"
    assert research["target"] == "example.com"
    assert usage["total_tokens"] == 150


@patch("aperix_geo.services.setup.llm.stages.generate_profile_summary_via_llm")
@patch("aperix_geo.services.setup.llm.stages.build_profile_summary_payload")
def test_run_profile_summary_stage(mock_payload, mock_llm) -> None:
    profile = normalize_niche_profile(
        {"company": "Example", "industry": "SaaS"},
        entity="example.com",
    )
    mock_payload.return_value = {"target": "example.com"}
    mock_llm.return_value = ("# Example\n\n## 概述\n测试\n\n## 竞品\n* **Rival**（rival.com）：同业", {})

    summary, usage = run_profile_summary_stage(
        profile=profile,
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        entity_key="example.com",
        competitors=[{"domain": "rival.com", "brand": "Rival", "summary": "同业竞品"}],
    )

    assert summary.startswith("# Example")
    assert "Rival" in summary
