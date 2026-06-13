"""Tests for snippet-based competitor brand extraction."""

from __future__ import annotations

import json
from unittest.mock import patch

from aperix_geo.services.competitor.selection import (
    normalize_snippet_competitor_brands,
    select_brand_names,
)
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.services.providers.prompts import (
    COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM,
    competitor_snippet_brand_extraction_user_content,
)
from aperix_geo.services.searxng import SearchHit


def _sample_profile() -> NicheProfile:
    return {
        "company": "Aperix",
        "industry": "企业级 API 网关",
        "core_features": "高并发路由, 零信任鉴权",
        "target_customers": "中大型 SaaS 技术团队",
        "micro_keywords": "API gateway, 微服务治理, 流量染色",
    }


def test_snippet_brand_extraction_user_content_includes_closed_set() -> None:
    text = competitor_snippet_brand_extraction_user_content(
        brand="Aperix",
        profile=_sample_profile(),
        region_label="中国大陆",
        language="zh-CN",
        search_block="1. 示例摘要",
        max_brands=5,
    )
    assert "闭集" in text
    assert "目标主体 A：Aperix" in text
    assert "微观利基画像" in text
    assert "brand_names" in text


def test_snippet_brand_extraction_system_is_separate_from_absa() -> None:
    assert "brand_names" in COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM
    assert "other_brands_sentiment_absa" not in COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM
    assert "brands_sentiment_absa" not in COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM


def test_normalize_snippet_competitor_brands_filters_closed_set_and_domains() -> None:
    data = {
        "brand_names": ["Aperix", "Beta", "beta.com", "Gamma", ""],
    }
    out = normalize_snippet_competitor_brands(data, target_brand="Aperix", max_brands=5)
    assert out == ["Beta", "Gamma"]


@patch("aperix_geo.services.competitor.selection.chat_completion")
def test_select_brand_names_skips_llm_when_no_hits(mock_chat) -> None:
    result = select_brand_names(
        _sample_profile(),
        brand="Aperix",
        pool=SearchPool(domains=[], hits=[]),
        region="CN",
        language="zh-CN",
    )
    assert result == []
    mock_chat.assert_not_called()


@patch("aperix_geo.services.competitor.selection.chat_completion")
def test_select_brand_names_parses_brand_names_array(mock_chat) -> None:
    mock_chat.return_value = (
        json.dumps({"brand_names": ["Beta", "Gamma"]}),
        {},
        100,
    )
    pool = SearchPool(
        domains=["digitaling.com"],
        hits=[
            SearchHit(
                url="https://digitaling.com/a",
                title="Beta vs Aperix",
                snippet="Beta 是企业级 API 网关竞品",
                query="API gateway 竞品",
            )
        ],
    )
    result = select_brand_names(
        _sample_profile(),
        brand="Aperix",
        pool=pool,
        region="CN",
        language="zh-CN",
    )
    assert result == ["Beta", "Gamma"]
    system_msg = mock_chat.call_args[0][0][0]["content"]
    user_msg = mock_chat.call_args[0][0][1]["content"]
    assert "brand_names" in system_msg
    assert "闭集" in user_msg
    assert "Beta vs Aperix" in user_msg
