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


def test_build_monitoring_topics_payload_includes_profile_and_exclusion() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测 SaaS",
            "core_features": ["AI 可见度"],
            "target_customers": "市场团队",
            "micro_keywords": ["AI 品牌可见度监测 SaaS"],
        },
        entity="sheepgeo.com",
    )
    payload = build_monitoring_topics_payload(
        research_payload={
            "mode": "domain",
            "target": "sheepgeo.com",
            "region": "中国大陆",
            "language": "简体中文",
            "site_data": {"title": "SheepGeo"},
        },
        profile=profile,
    )
    assert payload["niche_profile"]["industry"] == "GEO 监测 SaaS"
    assert payload["micro_keywords_for_exclusion"] == ["AI 品牌可见度监测 SaaS"]
    assert payload["site_context"]["title"] == "SheepGeo"
    assert "site_data" not in payload


def test_build_profile_summary_payload_includes_competitors() -> None:
    profile = normalize_niche_profile(
        {"industry": "GEO 监测 SaaS", "company": "SheepGeo"},
        entity="sheepgeo.com",
    )
    payload = build_profile_summary_payload(
        research_payload={
            "mode": "domain",
            "target": "sheepgeo.com",
            "region": "中国大陆",
            "language": "简体中文",
            "site_data": {"title": "SheepGeo"},
        },
        profile=profile,
        competitors=[{"domain": "rival.com", "brand": "Rival", "summary": "同业竞品"}],
    )
    assert payload["niche_profile"]["company"] == "SheepGeo"
    assert payload["competitors"][0]["brand"] == "Rival"
    assert "site_data" not in payload
    assert "web_research" not in payload


@patch("aperix_geo.services.setup.llm.stages.run_monitoring_topics_stage")
@patch("aperix_geo.services.setup.llm.stages.run_niche_profile_stage")
def test_build_subject_profile_runs_two_llm_stages(mock_niche, mock_topics) -> None:
    from aperix_geo.services.setup.llm.stages import build_subject_profile

    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测 SaaS",
            "micro_keywords": ["AI 品牌可见度监测 SaaS"],
        },
        entity="sheepgeo.com",
    )
    research = {"mode": "domain", "target": "sheepgeo.com"}
    mock_niche.return_value = (profile, research)
    mock_topics.return_value = ["AI 搜索可见度监测", "大模型引用优化"]

    result_profile, topics, result_research = build_subject_profile(
        subject_type="domain",
        target="sheepgeo.com",
        region="CN",
        language="zh-CN",
        website_url="sheepgeo.com",
    )

    mock_niche.assert_called_once()
    mock_topics.assert_called_once()
    assert result_profile["industry"] == "GEO 监测 SaaS"
    assert topics == ["AI 搜索可见度监测", "大模型引用优化"]
    assert result_research == research


@patch("aperix_geo.services.setup.llm.stages.generate_niche_profile_via_llm")
@patch("aperix_geo.services.setup.llm.payloads.build_subject_research_payload")
def test_run_niche_profile_stage(mock_payload, mock_llm) -> None:
    mock_payload.return_value = {"mode": "domain", "target": "example.com"}
    mock_llm.return_value = {
        "company": "Example",
        "industry": "跨境 B2B 支付",
        "core_features": ["收款"],
        "target_customers": "卖家",
        "micro_keywords": ["SMB 跨境收款 SaaS"],
    }

    profile, research = run_niche_profile_stage(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
        website_url="example.com",
    )

    assert profile["industry"] == "跨境 B2B 支付"
    assert research["target"] == "example.com"


@patch("aperix_geo.services.setup.llm.stages.generate_profile_summary_via_llm")
@patch("aperix_geo.services.setup.llm.stages.build_profile_summary_payload")
def test_run_profile_summary_stage(mock_payload, mock_llm) -> None:
    profile = normalize_niche_profile(
        {"company": "Example", "industry": "SaaS"},
        entity="example.com",
    )
    mock_payload.return_value = {"target": "example.com"}
    mock_llm.return_value = "# Example\n\n## 概述\n测试\n\n## 竞品\n* **Rival**（rival.com）：同业"

    summary = run_profile_summary_stage(
        profile=profile,
        research_payload={"mode": "domain"},
        entity_key="example.com",
        region="CN",
        subject_type="domain",
        competitors=[{"domain": "rival.com", "brand": "Rival", "summary": "同业竞品"}],
    )

    assert summary.startswith("# Example")
    assert "Rival" in summary
