"""Tests for brand-mode competitor name selection."""

from __future__ import annotations

import json
from unittest.mock import patch

from aperix_geo.services.competitor.selection import select_brand_names
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.services.providers.prompts import brand_selection_user_content
from aperix_geo.services.searxng import SearchHit


def _sample_profile() -> NicheProfile:
    return {
        "company": "Aperix",
        "industry": "企业级 API 网关",
        "core_features": "高并发路由, 零信任鉴权",
        "target_customers": "中大型 SaaS 技术团队",
        "micro_keywords": "API gateway, 微服务治理, 流量染色",
    }


def test_brand_selection_user_content_includes_niche_profile() -> None:
    text = brand_selection_user_content(
        brand="Aperix",
        profile=_sample_profile(),
        region_label="中国大陆",
        language="zh-CN",
        search_block="1. 示例摘要",
        max_brands=5,
    )
    assert "微观利基画像" in text
    assert "企业级 API 网关" in text
    assert "高并发路由" in text
    assert "API gateway" in text
    assert "最多 5 个" in text


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
def test_select_brand_names_parses_and_filters_domains(mock_chat) -> None:
    mock_chat.return_value = (
        json.dumps({"domains": ["beta.com"], "brand_names": ["Beta", "beta.com", "Gamma"]}),
        {},
        100,
    )
    pool = SearchPool(
        domains=["beta.com"],
        hits=[
            SearchHit(
                url="https://example.com/a",
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
    mock_chat.assert_called_once()
    user_msg = mock_chat.call_args[0][0][1]["content"]
    assert "搜索结果摘要" in user_msg
    assert "Beta vs Aperix" in user_msg
