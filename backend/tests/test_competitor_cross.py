"""Tests for cross-validation scoring."""

from unittest.mock import patch

from aperix_geo.services.competitor.cross_validate import (
    CompetitorScore,
    run_cross_validate,
)
from aperix_geo.services.competitor.types import SearchPool, SiteHead
from aperix_geo.services.web_search import SearchHit


def _profile():
    return {
        "company": "空中云汇",
        "industry": "跨境支付",
        "core_features": "跨境收款",
        "target_customers": "跨境电商",
        "micro_keywords": "跨境支付 SaaS",
    }


@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_cross_validate_empty_pool(mock_settings) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    result = run_cross_validate(
        _profile(),
        target_domain="airwallex.com",
        pool=SearchPool(domains=[], hits=[]),
    )
    assert result.scores == []
    assert result.heads == {}


@patch("aperix_geo.services.competitor.cross_validate._score_batch")
@patch("aperix_geo.services.competitor.cross_validate.fetch_site_heads")
@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_cross_validate_batches(mock_settings, mock_fetch, mock_score) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_min_score = 6.0

    mock_fetch.return_value = {
        "wise.com": SiteHead("wise.com", "Wise", "跨境", True),
        "paypal.com": SiteHead("paypal.com", "PayPal", "支付", True),
        "stripe.com": SiteHead("stripe.com", "Stripe", "支付", True),
    }
    mock_score.return_value = [
        CompetitorScore("wise.com", 9.0, "直接竞品"),
        CompetitorScore("paypal.com", 4.0, "体量不匹配"),
        CompetitorScore("stripe.com", 7.5, "部分重叠"),
    ]

    pool = SearchPool(
        domains=["wise.com", "paypal.com", "stripe.com"],
        hits=[],
        hit_by_domain={"wise.com": SearchHit("Wise", "https://wise.com", "snippet", "q")},
    )
    result = run_cross_validate(_profile(), target_domain="airwallex.com", pool=pool)
    assert mock_score.call_count == 1
    assert {s.domain for s in result.scores} == {"wise.com", "paypal.com", "stripe.com"}
    assert result.scores[0].domain == "wise.com"


@patch("aperix_geo.services.competitor.cross_validate._score_batch")
@patch("aperix_geo.services.competitor.cross_validate.fetch_site_heads")
@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_unreachable_hosts_skip_llm(mock_settings, mock_fetch, mock_score) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_min_score = 6.0
    mock_fetch.return_value = {
        "good.com": SiteHead("good.com", "Good", "ok", True),
        "bad.com": SiteHead("bad.com", "", "", False),
    }
    mock_score.return_value = [CompetitorScore("good.com", 8.0, "竞品")]

    pool = SearchPool(domains=["good.com", "bad.com"], hits=[], hit_by_domain={})
    result = run_cross_validate(
        {
            "company": "测试",
            "industry": "跨境药品",
            "core_features": "直购",
            "target_customers": "B2B",
            "micro_keywords": "跨境药品平台",
        },
        target_domain="target.com",
        pool=pool,
    )

    mock_score.assert_called_once()
    payload = mock_score.call_args[0][1]
    assert len(payload) == 1
    assert payload[0]["domain"] == "good.com"
    bad = next(s for s in result.scores if s.domain == "bad.com")
    assert bad.score == 0.0
    assert "不可打开" in bad.reason
