"""Tests for Setup LLM stages and payloads."""

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.llm.stages import (
    run_niche_profile_stage,
    run_profile_summary_stage,
)


@patch("aperix_geo.services.setup.llm.stages.generate_niche_profile_via_llm")
@patch("aperix_geo.services.setup.llm.payloads.build_subject_research_payload")
def test_run_niche_profile_stage(mock_payload, mock_llm) -> None:
    mock_payload.return_value = {"mode": "domain", "target": "example.com"}
    mock_llm.return_value = (
        {
            "company": "Example",
            "industry": "SaaS",
            "keywords": "可见度监测、品牌引用",
            "brief": "市场团队",
        },
        {"total_tokens": 10},
    )

    profile, research, usage = run_niche_profile_stage(
        subject_type="domain",
        target="example.com",
        region="CN",
        language="zh-CN",
    )

    assert profile["industry"] == "SaaS"
    assert research["mode"] == "domain"
    assert usage["total_tokens"] == 10
    mock_llm.assert_called_once()


@patch("aperix_geo.services.setup.llm.stages.generate_niche_profile_via_llm")
@patch("aperix_geo.services.setup.llm.payloads.build_subject_research_payload")
def test_run_niche_profile_stage_retries_on_invalid(mock_payload, mock_llm) -> None:
    mock_payload.return_value = {"mode": "domain", "target": "example.com"}
    bad = {
        "company": "Example",
        "industry": "未知行业",
        "keywords": "",
        "brief": "",
    }
    good = {
        "company": "Example",
        "industry": "跨境 B2B 支付",
        "keywords": "跨境收款、多币种账户",
        "brief": "卖家",
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


def test_run_profile_summary_stage_uses_fallback() -> None:
    profile = normalize_niche_profile(
        {"company": "Example", "industry": "SaaS", "keywords": "可见度", "brief": "市场"},
        entity="example.com",
    )

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
    assert usage == {}
