"""Tests for query style helpers."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.setup.query_style import validate_search_queries_style
from aperix_geo.services.setup.query_style_llm import evaluate_query_style_via_llm


def test_validate_search_queries_style_checks_skeleton_diversity() -> None:
    profile = normalize_niche_profile(
        {
            "topic_lexicon": {
                "category_terms": ["GEO品牌监测", "AI品牌可见度"],
                "scenario_terms": ["多平台对比分析"],
                "audience_terms": ["品牌营销人员"],
                "pain_terms": ["难以量化可见度"],
            },
            "search_queries": [
                "GEO品牌监测在多平台结果里差很多正常吗",
                "AI品牌可见度在AI搜索里看不到怎么办",
            ],
        },
        entity="example.com",
    )
    plan = build_keyword_plan(profile)
    validate_search_queries_style(plan["long_tail_examples"], plan=plan)


@patch("aperix_geo.services.setup.query_style_llm.chat_completion")
def test_evaluate_query_style_via_llm_returns_feedback(mock_chat) -> None:
    mock_chat.return_value = (
        '{"pass": false, "feedback": ["search_queries 多条像标题体，须改为口述问句"]}',
        {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        10,
    )
    feedback, usage = evaluate_query_style_via_llm(
        stage="profile",
        groups=[{"label": "search_queries", "queries": ["GEO品牌监测基础概念"]}],
        entity_key="example.com",
    )
    assert feedback == ["search_queries 多条像标题体，须改为口述问句"]
    assert usage["total_tokens"] == 2


@patch("aperix_geo.services.setup.query_style_llm.chat_completion")
def test_evaluate_query_style_via_llm_passes(mock_chat) -> None:
    mock_chat.return_value = (
        '{"pass": true, "feedback": []}',
        {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        10,
    )
    feedback, usage = evaluate_query_style_via_llm(
        stage="profile",
        groups=[{"label": "search_queries", "queries": ["GEO品牌监测怎么做"]}],
        entity_key="example.com",
    )
    assert feedback == []
    assert usage["total_tokens"] == 2
