"""Tests for SearXNG candidate pool."""

from unittest.mock import patch

from aperix_geo.services.competitor.cross_validate import CompetitorScore, expand_ranked_domains
from aperix_geo.services.competitor.search import run_search_query, search_candidate_domains
from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.competitor.types import CrossValidateResult
from aperix_geo.services.searxng import SearchHit


def _sample_profile():
    return normalize_niche_profile(
        {
            "company": "空中云汇",
            "industry": "跨境支付",
            "core_features": ["跨境收款", "多币种账户"],
            "target_customers": "跨境电商卖家",
            "micro_keywords": ["跨境收款", "多币种账户"],
        },
        entity="airwallex.com",
    )


@patch("aperix_geo.services.competitor.search.search_text")
@patch("aperix_geo.services.competitor.search.get_settings")
@patch("aperix_geo.services.competitor.search.host_resolves", return_value=True)
def test_search_candidate_domains(_mock_dns, mock_settings, mock_search) -> None:
    mock_settings.return_value.searxng_base_url = "http://127.0.0.1:8061"
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_search_rounds = 3
    hits = [
        SearchHit(title="Wise 官网", url="https://wise.com/business", snippet="pay", query="q"),
        SearchHit(title="PayPal 官方", url="https://www.paypal.com/", snippet="pay", query="q"),
        SearchHit(title="十大排名", url="https://36kr.com/p/1", snippet="", query="q"),
    ]
    mock_search.return_value = hits
    pool = search_candidate_domains(_sample_profile(), exclude_domain="airwallex.com")
    assert "wise.com" in pool.domains
    assert "paypal.com" in pool.domains
    assert "36kr.com" not in pool.domains
    assert mock_search.call_count == 3
    assert "wise.com" in pool.hit_by_domain


@patch("aperix_geo.services.competitor.search.RESULT_MIN", 2)
@patch("aperix_geo.services.competitor.search.search_text")
@patch("aperix_geo.services.competitor.search.get_settings")
@patch("aperix_geo.services.competitor.search.host_resolves", return_value=True)
def test_pool_from_web_research_rows_seeds_candidate_pool(_mock_dns, mock_settings, mock_search) -> None:
    from aperix_geo.services.competitor.search import pool_from_web_research_rows, search_candidate_domains

    mock_settings.return_value.searxng_base_url = "http://127.0.0.1:8061"
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_search_rounds = 3

    seed = pool_from_web_research_rows(
        [
            {"title": "Wise", "url": "https://wise.com", "snippet": "pay"},
            {"title": "PayPal", "url": "https://paypal.com", "snippet": "pay"},
        ],
        exclude_domain=None,
    )
    assert len(seed.domains) >= 2
    pool = search_candidate_domains(_sample_profile(), exclude_domain="airwallex.com", initial_pool=seed)
    assert len(pool.domains) >= 2
    mock_search.assert_not_called()


@patch("aperix_geo.services.competitor.search.search_text")
@patch("aperix_geo.services.competitor.search.get_settings")
@patch("aperix_geo.services.competitor.search.host_resolves", return_value=True)
def test_search_candidate_domains_stops_when_pool_is_full(_mock_dns, mock_settings, mock_search) -> None:
    mock_settings.return_value.searxng_base_url = "http://127.0.0.1:8061"
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_search_rounds = 5
    mock_settings.return_value.competitor_result_min = 2
    hits = [
        SearchHit(title="Wise 官网", url="https://wise.com/business", snippet="pay", query="q"),
        SearchHit(title="PayPal 官方", url="https://www.paypal.com/", snippet="pay", query="q"),
        SearchHit(title="Stripe", url="https://stripe.com/", snippet="pay", query="q"),
    ]
    mock_search.return_value = hits
    pool = search_candidate_domains(_sample_profile(), exclude_domain="airwallex.com")
    assert len(pool.domains) >= 2
    assert mock_search.call_count == 1


@patch("aperix_geo.services.competitor.search.search_text")
@patch("aperix_geo.services.competitor.search.get_settings")
@patch("aperix_geo.services.competitor.search.host_resolves", return_value=True)
def test_run_search_query_merges_into_pool(_mock_dns, mock_settings, mock_search) -> None:
    mock_settings.return_value.searxng_base_url = "http://127.0.0.1:8061"
    mock_settings.return_value.competitor_pool_size = 50
    profile = _sample_profile()
    mock_search.side_effect = [
        [SearchHit(title="Wise", url="https://wise.com", snippet="", query="q1")],
        [SearchHit(title="Stripe", url="https://stripe.com", snippet="", query="q2")],
    ]
    pool = run_search_query(profile, "q1", exclude_domain="airwallex.com")
    pool = run_search_query(profile, "q2", exclude_domain="airwallex.com", pool=pool)
    assert mock_search.call_count == 2
    assert set(pool.domains) == {"wise.com", "stripe.com"}


def test_expand_ranked_excludes_below_min_score() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("paypal.com", 8.5, "同赛道支付"),
            CompetitorScore("noise.com", 3.0, "媒体"),
        ],
        heads={},
    )
    ordered = expand_ranked_domains(validation, min_score=6.0, max_keep=10)
    assert ordered == ["paypal.com"]
