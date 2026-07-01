"""Tests for Doubao web-search competitor discovery."""

from __future__ import annotations

import json
from unittest.mock import patch

from aperix_geo.services.competitor.doubao import discover_competitors_via_doubao
from aperix_geo.services.competitor.parse import parse_doubao_competitors_payload
from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.providers.result import SamplingChatResult


def _sample_profile():
    return normalize_niche_profile(
        {
            "company": "SheepGeo",
            "industry": "生成式引擎优化(GEO)分析平台",
            "features": "AI 可见性检测",
            "customers": "品牌市场团队",
            "keywords": ["GEO 平台", "AI 可见性检测"],
        },
        entity="sheepgeo.com",
    )


def test_parse_doubao_competitors_payload_filters_self() -> None:
    text = """
    {"competitors": [
      {"domain": "sheepgeo.com", "website_url": "https://sheepgeo.com", "brand": "SheepGeo", "summary": "self"},
      {"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound", "aliases": ["Profound AI"], "summary": "GEO 监测"},
      {"domain": "36kr.com", "website_url": "https://36kr.com", "brand": "36氪", "summary": "媒体"}
    ]}
    """
    items = parse_doubao_competitors_payload(
        text,
        mode="domain",
        self_domain="sheepgeo.com",
    )
    assert len(items) == 2
    assert {item["domain"] for item in items} == {"profound.ai", "36kr.com"}


def test_parse_keeps_empty_aliases() -> None:
    text = """
    {"competitors": [
      {"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound", "aliases": []},
      {"domain": "otterly.ai", "website_url": "https://otterly.ai", "brand": "Otterly", "aliases": ["Otterly AI"]}
    ]}
    """
    items = parse_doubao_competitors_payload(
        text,
        mode="domain",
        self_domain="sheepgeo.com",
    )
    assert len(items) == 2
    assert items[0]["domain"] == "profound.ai"
    assert "aliases" not in items[0]
    assert items[1]["aliases"] == ["Otterly AI"]


def test_parse_keeps_all_valid_rows() -> None:
    rows = [
        {"domain": f"c{i}.com", "website_url": f"https://c{i}.com", "brand": f"C{i}"}
        for i in range(10)
    ]
    text = json.dumps({"competitors": rows}, ensure_ascii=False)
    items = parse_doubao_competitors_payload(
        text,
        mode="domain",
        self_domain="sheepgeo.com",
    )
    assert len(items) == 10
    assert items[-1]["domain"] == "c9.com"


def test_parse_uses_domain_when_website_url_missing() -> None:
    text = """
    {"competitors": [
      {"domain": "ghost.io", "brand": "Ghost", "website_url": ""},
      {"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound", "aliases": ["Profound AI"]}
    ]}
    """
    items = parse_doubao_competitors_payload(
        text,
        mode="domain",
        self_domain="sheepgeo.com",
    )
    assert len(items) == 2
    assert items[0]["domain"] == "ghost.io"
    assert items[0]["website_url"] == "ghost.io"
    assert items[1]["domain"] == "profound.ai"


def test_parse_brand_mode_dedupes_by_brand() -> None:
    text = """
    {"competitors": [
      {"brand": "深睿医疗", "domain": "ignore.com", "website_url": "https://ignore.com"},
      {"brand": "深睿医疗", "domain": "", "website_url": ""}
    ]}
    """
    items = parse_doubao_competitors_payload(
        text,
        mode="brand",
        self_brand="联影智能",
    )
    assert len(items) == 1
    assert items[0]["brand"] == "深睿医疗"
    assert items[0]["domain"] == "ignore.com"
    assert items[0]["website_url"] == "https://ignore.com"


def test_parse_brand_mode_keeps_website_url_candidate() -> None:
    text = """
    {"competitors": [
      {"brand": "大益", "domain": "fake.com", "website_url": "https://fake.com", "aliases": ["大益茶业"]}
    ]}
    """
    items = parse_doubao_competitors_payload(
        text,
        mode="brand",
        self_brand="八马茶业",
    )
    assert len(items) == 1
    assert items[0]["brand"] == "大益"
    assert items[0]["domain"] == "fake.com"
    assert items[0]["website_url"] == "https://fake.com"
    assert items[0]["aliases"] == ["大益茶业"]


def test_parse_brand_mode_filters_self() -> None:
    text = '{"competitors": [{"brand": "联影智能", "domain": "", "website_url": ""}]}'
    items = parse_doubao_competitors_payload(
        text,
        mode="brand",
        self_brand="联影智能",
    )
    assert items == []


@patch("aperix_geo.services.competitor.doubao.doubao_responses_chat")
@patch("aperix_geo.services.competitor.doubao.get_settings")
def test_discover_competitors_via_doubao(mock_settings, mock_chat) -> None:
    mock_settings.return_value.doubao_api_key = "sk-test"
    mock_settings.return_value.doubao_base_url = "https://ark.example.com/api/v3"
    mock_settings.return_value.doubao_model = "doubao-test"
    mock_settings.return_value.doubao_web_search_enabled = True
    mock_settings.return_value.doubao_responses_timeout_s = 60.0

    mock_chat.return_value = SamplingChatResult(
        text='{"competitors": [{"domain": "profound.ai", "website_url": "https://profound.ai", "brand": "Profound", "aliases": ["Profound AI"]}]}',
        usage={},
        latency_ms=100,
        web_search_mode="doubao_native",
    )

    items = discover_competitors_via_doubao(
        _sample_profile(),
        subject_type="domain",
        target="sheepgeo.com",
        website_url="https://sheepgeo.com",
    )
    assert len(items) == 1
    assert items[0]["domain"] == "profound.ai"
    assert items[0]["website_url"] == "https://profound.ai"
    mock_chat.assert_called_once()


@patch("aperix_geo.services.competitor.discover.discover_competitors_via_doubao")
def test_discover_domain_returns_empty_when_doubao_fails(mock_doubao) -> None:
    from aperix_geo.services.competitor.discover import discover_competitors

    mock_doubao.side_effect = RuntimeError("api down")

    result = discover_competitors(_sample_profile(), subject_type="domain", target="sheepgeo.com")
    assert result == {"competitors": [], "discovery_source": "doubao"}


@patch("aperix_geo.services.competitor.discover.enrich_discovered_competitors", side_effect=lambda c, **_: c)
@patch("aperix_geo.services.competitor.discover.get_settings")
@patch("aperix_geo.services.competitor.discover.run_cross_validate")
@patch("aperix_geo.services.competitor.discover.discover_competitors_via_doubao")
def test_discover_domain_uses_doubao(mock_doubao, mock_cv, mock_settings, mock_enrich) -> None:
    from aperix_geo.services.competitor.discover import discover_competitors
    from aperix_geo.services.competitor.types import CompetitorScore, CrossValidateResult, SiteHead

    mock_settings.return_value.competitor_result_min = 3
    mock_settings.return_value.competitor_search_rounds = 1
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_result_max = 5
    mock_doubao.return_value = [
        {"domain": "a.com", "website_url": "https://a.com", "brand": "A", "aliases": ["A Inc"]},
        {"domain": "b.com", "website_url": "https://b.com", "brand": "B", "aliases": ["B Co"]},
        {"domain": "c.com", "website_url": "https://c.com", "brand": "C"},
    ]
    mock_cv.return_value = CrossValidateResult(
        scores=[
            CompetitorScore("a.com", 8.0, "ok"),
            CompetitorScore("b.com", 7.0, "ok"),
            CompetitorScore("c.com", 7.0, "ok"),
        ],
        heads={
            "a.com": SiteHead("a.com", "A", "", True),
            "b.com": SiteHead("b.com", "B", "", True),
            "c.com": SiteHead("c.com", "C", "", True),
        },
    )

    result = discover_competitors(_sample_profile(), subject_type="domain", target="sheepgeo.com")
    assert result["discovery_source"] == "doubao"
    assert len(result["competitors"]) == 3
    assert {c["domain"] for c in result["competitors"]} == {"a.com", "b.com", "c.com"}
    mock_doubao.assert_called_once()
    mock_cv.assert_called_once()
    mock_enrich.assert_called_once()


@patch("aperix_geo.services.competitor.discover.enrich_discovered_competitors", side_effect=lambda c, **_: c)
@patch("aperix_geo.services.competitor.discover.get_settings")
@patch("aperix_geo.services.competitor.discover.run_cross_validate")
@patch("aperix_geo.services.competitor.discover.discover_competitors_via_doubao")
def test_doubao_retries_when_cross_validate_below_min(
    mock_doubao,
    mock_cv,
    mock_settings,
    mock_enrich,
) -> None:
    from aperix_geo.services.competitor.discover import discover_competitors
    from aperix_geo.services.competitor.types import CompetitorScore, CrossValidateResult, SiteHead

    mock_settings.return_value.competitor_result_min = 3
    mock_settings.return_value.competitor_search_rounds = 2
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_result_max = 5
    batch1 = [
        {"domain": "a.com", "website_url": "https://a.com", "brand": "A"},
        {"domain": "b.com", "website_url": "https://b.com", "brand": "B"},
    ]
    batch2 = [
        {"domain": "c.com", "website_url": "https://c.com", "brand": "C"},
    ]
    mock_doubao.side_effect = [batch1, batch2]

    def _cv_result(profile, *, pool, **_kwargs):
        scores = [
            CompetitorScore(d, 8.0, "ok")
            for d in pool.domains
            if d in {"a.com", "b.com", "c.com"}
        ]
        heads = {
            d: SiteHead(d, d.upper(), "", True)
            for d in pool.domains
            if d in {"a.com", "b.com", "c.com"}
        }
        return CrossValidateResult(scores=scores, heads=heads)

    mock_cv.side_effect = _cv_result

    result = discover_competitors(_sample_profile(), subject_type="domain", target="sheepgeo.com")
    assert len(result["competitors"]) == 3
    assert mock_doubao.call_count == 2
    assert mock_cv.call_count == 2


@patch("aperix_geo.services.competitor.discover.enrich_discovered_competitors", side_effect=lambda c, **_: c)
@patch("aperix_geo.services.competitor.discover.reconcile_brand_competitor_domains")
@patch("aperix_geo.services.competitor.discover.get_settings")
@patch("aperix_geo.services.competitor.discover.discover_competitors_via_doubao")
def test_discover_brand_resolves_domains_via_searxng(
    mock_doubao,
    mock_settings,
    mock_reconcile,
    mock_enrich,
) -> None:
    from aperix_geo.services.competitor.discover import discover_competitors

    mock_settings.return_value.competitor_result_min = 2
    mock_settings.return_value.competitor_search_rounds = 1
    mock_settings.return_value.competitor_result_max = 5
    mock_doubao.return_value = [
        {"domain": "", "website_url": "", "brand": "竞品 A"},
        {"domain": "", "website_url": "", "brand": "竞品 B"},
    ]
    mock_reconcile.return_value = (
        [
            {"domain": "a.com", "website_url": "https://a.com", "brand": "竞品 A"},
            {"domain": "", "website_url": "", "brand": "竞品 B"},
        ],
        {},
    )

    result = discover_competitors(
        _sample_profile(),
        subject_type="brand",
        target="SheepGeo",
        region="CN",
        language="zh-CN",
    )
    assert result["discovery_source"] == "doubao"
    assert len(result["competitors"]) == 2
    mock_reconcile.assert_called_once()
    mock_enrich.assert_called_once()
