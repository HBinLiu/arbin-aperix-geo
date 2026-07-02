"""Tests for Setup LLM stages and payloads."""

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.llm.payloads import (
    build_profile_summary_payload,
    build_topic_plan_payload,
)
from aperix_geo.services.setup.llm.stages import (
    run_niche_profile_stage,
    run_profile_summary_stage,
)


def test_build_topic_plan_payload_includes_profile() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO 监测 SaaS",
            "features": ["AI 可见度", "品牌引用分析", "多平台监测"],
            "customers": "市场团队",
            "search_queries": [
                "AI可见度监测市场团队",
                "品牌引用分析SEO团队",
                "多平台监测竞品对标",
            ],
            "topic_lexicon": {
                "category_terms": ["AI 可见度监测", "品牌搜索可见度", "多平台GEO监测"],
                "scenario_terms": ["品牌监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["引用率"],
            },
        },
        entity="sheepgeo.com",
    )
    payload = build_topic_plan_payload(
        subject_type="domain",
        target="sheepgeo.com",
        profile=profile,
        competitors=[{"brand": "同业竞品 A", "summary": "同业竞品 A"}],
    )
    assert payload["subject_type"] == "domain"
    assert payload["target"] == "sheepgeo.com"
    assert payload["niche_profile"]["company"] == "sheepgeo.com"
    assert payload["niche_profile"]["industry"] == "GEO 监测 SaaS"
    assert "category_terms" in payload["niche_profile"]
    assert payload["competitor_scenarios"] == ["同业竞品 A"]
    assert payload["topic_guidance"]["topic_count"] == 5
    assert payload["topic_guidance"]["min_core_keyword_topics"] >= 1
    assert "keyword_plan" in payload
    assert payload["keyword_plan"]["core_keywords"]


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
            "features": ["跨境收款", "多币种账户", "企业钱包"],
            "customers": "卖家",
            "search_queries": [
                "跨境收款SMB卖家",
                "多币种账户企业钱包",
                "企业钱包到账时效",
                "跨境结汇卖家怎么选",
                "全球收款到账时效",
            ],
            "topic_lexicon": {
                "category_terms": [
                    "跨境收款",
                    "多币种账户",
                    "企业钱包",
                    "跨境结汇",
                    "全球收款",
                ],
                "scenario_terms": ["SMB 收款"],
                "audience_terms": ["卖家"],
                "pain_terms": ["到账时效"],
            },
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
    mock_llm.assert_called_once()


@patch("aperix_geo.services.setup.llm.stages.generate_niche_profile_via_llm")
@patch("aperix_geo.services.setup.llm.payloads.build_subject_research_payload")
def test_run_niche_profile_stage_retries_on_validation_failure(mock_payload, mock_llm) -> None:
    mock_payload.return_value = {"mode": "domain", "target": "example.com"}
    bad = {
        "company": "Example",
        "industry": "跨境 B2B 支付",
        "features": ["跨境收款"],
        "customers": "卖家",
        "search_queries": ["到账时效问题"],
        "topic_lexicon": {
            "category_terms": ["跨境收款"],
            "scenario_terms": ["SMB 收款"],
            "audience_terms": ["卖家"],
            "pain_terms": ["到账时效"],
        },
    }
    good = {
        **bad,
        "features": ["跨境收款", "多币种账户", "企业钱包"],
        "search_queries": [
            "跨境收款SMB卖家",
            "多币种账户企业钱包",
            "企业钱包到账时效",
            "跨境结汇卖家怎么选",
            "全球收款到账时效",
        ],
        "topic_lexicon": {
            **bad["topic_lexicon"],
            "category_terms": [
                "跨境收款",
                "多币种账户",
                "企业钱包",
                "跨境结汇",
                "全球收款",
            ],
        },
    }
    mock_llm.side_effect = [
        (bad, {"total_tokens": 10}),
        (good, {"total_tokens": 20}),
    ]

    profile, _, usage = run_niche_profile_stage(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
    )

    assert profile["industry"] == "跨境 B2B 支付"
    assert usage["total_tokens"] >= 20
    assert mock_llm.call_count == 2
    assert "validation_feedback" in mock_llm.call_args_list[1].kwargs["user_payload"]


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
