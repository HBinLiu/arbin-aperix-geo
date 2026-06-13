"""Tests for snippet-based competitor domain resolution."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.competitor.snippet import (
    augment_pool_from_snippet_brands,
    resolve_brand_official_domain_from_pool,
)
from aperix_geo.services.competitor.types import SearchPool
from aperix_geo.services.searxng import SearchHit


def _sample_profile():
    return normalize_niche_profile(
        {
            "company": "SheepGeo",
            "industry": "生成式引擎优化(GEO)分析平台",
            "core_features": "AI 可见性检测",
            "target_customers": "品牌市场团队",
            "micro_keywords": ["GEO 平台", "AI 可见性检测"],
        },
        entity="sheepgeo.com",
    )


def _article_pool() -> SearchPool:
    hit = SearchHit(
        title="2025 GEO 工具对比：Profound vs Otterly",
        url="https://digitaling.com/articles/geo-tools",
        snippet="Profound 与 Otterly 是主流 GEO 监测平台，适合品牌团队。",
        query="GEO 平台 竞品",
    )
    return SearchPool(
        domains=["digitaling.com"],
        hits=[hit],
        hit_by_domain={"digitaling.com": hit},
    )


@patch("aperix_geo.services.competitor.snippet.enrich_hit_urls", return_value={})
@patch("aperix_geo.services.competitor.snippet.host_resolves", return_value=True)
@patch("aperix_geo.services.competitor.snippet.search_brand_official_domain")
@patch("aperix_geo.services.competitor.snippet.select_brand_names")
def test_augment_pool_resolves_official_domains(
    mock_select,
    mock_search_domain,
    _mock_dns,
    _mock_enrich,
) -> None:
    mock_select.return_value = ["Profound", "Otterly"]
    mock_search_domain.side_effect = ["profound.ai", "otterly.ai"]

    pool, added = augment_pool_from_snippet_brands(
        _sample_profile(),
        _article_pool(),
        domain="sheepgeo.com",
        region="CN",
        language="zh-CN",
    )

    assert added == ["profound.ai", "otterly.ai"]
    assert "profound.ai" in pool.domains
    assert "otterly.ai" in pool.domains
    assert pool.hit_by_domain["profound.ai"].query == "setup:snippet"
    mock_search_domain.assert_any_call("Profound")
    mock_search_domain.assert_any_call("Otterly")


@patch("aperix_geo.services.competitor.snippet.search_brand_official_domain", return_value="")
def test_resolve_prefers_domain_near_brand_in_snippets(mock_search) -> None:
    pool = _article_pool()
    domain = resolve_brand_official_domain_from_pool("Profound", pool)
    assert domain == ""
    mock_search.assert_called_once_with("Profound")

    mock_search.reset_mock()
    pool.hits[0] = SearchHit(
        title="GEO 工具榜单",
        url="https://digitaling.com/list",
        snippet="Profound（profound.ai）与 Otterly 是主流 GEO 平台。",
        query="GEO 平台 竞品",
    )
    domain = resolve_brand_official_domain_from_pool("Profound", pool)
    assert domain == "profound.ai"
    mock_search.assert_not_called()


@patch("aperix_geo.services.competitor.snippet.enrich_hit_urls", return_value={})
@patch("aperix_geo.services.competitor.snippet.select_brand_names", return_value=[])
def test_augment_skips_when_no_brands_extracted(mock_select, _mock_enrich) -> None:
    pool, added = augment_pool_from_snippet_brands(
        _sample_profile(),
        _article_pool(),
        domain="sheepgeo.com",
        region="CN",
        language="zh-CN",
    )
    assert added == []
    assert pool.domains == ["digitaling.com"]
    mock_select.assert_called_once()


@patch("aperix_geo.services.competitor.pipeline.enrich_discovered_competitors", side_effect=lambda c, **_: c)
@patch("aperix_geo.services.competitor.pipeline.package_discovered_competitors")
@patch("aperix_geo.services.competitor.pipeline.run_cross_validate")
@patch("aperix_geo.services.competitor.snippet.augment_pool_from_snippet_brands")
@patch("aperix_geo.services.competitor.pipeline.run_search_query")
@patch("aperix_geo.services.competitor.pipeline.planned_search_queries", return_value=["q1"])
@patch("aperix_geo.services.competitor.pipeline.get_settings")
def test_domain_pipeline_runs_snippet_when_underfilled(
    mock_settings,
    _mock_queries,
    mock_run_search,
    mock_augment,
    mock_cross,
    mock_package,
    _mock_enrich,
) -> None:
    from aperix_geo.services.competitor.cross_validate import CompetitorScore, CrossValidateResult
    from aperix_geo.services.competitor.pipeline import search_domain_competitors
    from aperix_geo.services.competitor.types import SiteHead

    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_pool_size = 50

    pool = _article_pool()
    mock_run_search.return_value = pool
    mock_augment.return_value = (pool, ["profound.ai"])

    heads = {"profound.ai": SiteHead("profound.ai", "Profound", "GEO", True)}
    mock_cross.side_effect = [
        CrossValidateResult(scores=[CompetitorScore("digitaling.com", 3.0, "媒体")], heads=heads),
        CrossValidateResult(
            scores=[
                CompetitorScore("digitaling.com", 3.0, "媒体"),
                CompetitorScore("profound.ai", 8.0, "同业 GEO"),
            ],
            heads=heads,
        ),
    ]
    mock_package.side_effect = [[], [{"domain": "profound.ai", "website_url": "", "brand": "", "summary": ""}]]

    result = search_domain_competitors(_sample_profile(), "sheepgeo.com")

    mock_augment.assert_called_once()
    assert mock_cross.call_count == 2
    assert len(result["competitors"]) == 1
    assert result["competitors"][0]["domain"] == "profound.ai"


@patch("aperix_geo.services.competitor.pipeline.enrich_discovered_competitors", side_effect=lambda c, **_: c)
@patch("aperix_geo.services.competitor.pipeline.package_discovered_competitors")
@patch("aperix_geo.services.competitor.pipeline.run_cross_validate")
@patch("aperix_geo.services.competitor.snippet.augment_pool_from_snippet_brands")
@patch("aperix_geo.services.competitor.pipeline.run_search_query")
@patch("aperix_geo.services.competitor.pipeline.planned_search_queries", return_value=["q1", "q2"])
@patch("aperix_geo.services.competitor.pipeline.get_settings")
def test_domain_pipeline_snippet_stops_before_second_searxng_round(
    mock_settings,
    _mock_queries,
    mock_run_search,
    mock_augment,
    mock_cross,
    mock_package,
    _mock_enrich,
) -> None:
    from aperix_geo.services.competitor.cross_validate import CompetitorScore, CrossValidateResult
    from aperix_geo.services.competitor.pipeline import search_domain_competitors
    from aperix_geo.services.competitor.types import SiteHead

    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_pool_size = 50

    pool = _article_pool()
    mock_run_search.return_value = pool
    mock_augment.return_value = (pool, ["profound.ai"])

    heads = {
        "digitaling.com": SiteHead("digitaling.com", "媒体", "榜单", True),
        "profound.ai": SiteHead("profound.ai", "Profound", "GEO", True),
    }
    mock_cross.side_effect = [
        CrossValidateResult(scores=[CompetitorScore("digitaling.com", 3.0, "媒体")], heads=heads),
        CrossValidateResult(
            scores=[
                CompetitorScore("digitaling.com", 3.0, "媒体"),
                CompetitorScore("profound.ai", 8.0, "同业 GEO"),
                CompetitorScore("otterly.ai", 7.5, "同业 GEO"),
                CompetitorScore("acme.com", 7.0, "同业"),
            ],
            heads={
                **heads,
                "otterly.ai": SiteHead("otterly.ai", "Otterly", "GEO", True),
                "acme.com": SiteHead("acme.com", "Acme", "GEO", True),
            },
        ),
    ]
    mock_package.return_value = [{"domain": "profound.ai", "website_url": "", "brand": "", "summary": ""}]

    search_domain_competitors(_sample_profile(), "sheepgeo.com")

    mock_run_search.assert_called_once()
    mock_augment.assert_called_once()
    assert mock_cross.call_count == 2
