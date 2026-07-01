"""Tests for cross-validation scoring."""

from unittest.mock import patch

from aperix_geo.services.competitor.cross_validate import (
    CompetitorScore,
    _candidate_payload,
    _target_payload,
    expand_ranked_domains,
    run_cross_validate,
)
from aperix_geo.services.competitor.types import CandidateMeta, CandidatePool, CrossValidateResult, SiteHead


def _profile():
    return {
        "company": "空中云汇",
        "industry": "跨境支付",
        "features": "跨境收款",
        "customers": "跨境电商",
        "search_queries": "跨境支付 SaaS",
    }


@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_cross_validate_empty_pool(mock_settings) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    result = run_cross_validate(
        _profile(),
        target_domain="airwallex.com",
        pool=CandidatePool(domains=[]),
    )
    assert result.scores == []
    assert result.heads == {}


def test_target_payload_includes_site_head() -> None:
    head = SiteHead(
        "airwallex.com",
        "Airwallex",
        "全球跨境支付",
        True,
        seo="schema: FinancialService",
    )
    payload = _target_payload(_profile(), target_domain="airwallex.com", head=head)
    assert payload["title"] == "Airwallex"
    assert payload["description"] == "全球跨境支付"
    assert "FinancialService" in payload["seo"]
    assert payload["industry"] == "跨境支付"


@patch("aperix_geo.services.competitor.cross_validate._score_batch")
@patch("aperix_geo.services.competitor.cross_validate.fetch_site_heads")
@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_cross_validate_batches(mock_settings, mock_fetch, mock_score) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_cross_validate_batch_size = 20

    mock_fetch.side_effect = [
        {"airwallex.com": SiteHead("airwallex.com", "Airwallex", "跨境支付平台", True)},
        {
            "wise.com": SiteHead("wise.com", "Wise", "跨境", True),
            "paypal.com": SiteHead("paypal.com", "PayPal", "支付", True),
            "stripe.com": SiteHead("stripe.com", "Stripe", "支付", True),
        },
    ]
    mock_score.return_value = [
        CompetitorScore("wise.com", 9.0, "直接竞品"),
        CompetitorScore("paypal.com", 4.0, "体量不匹配"),
        CompetitorScore("stripe.com", 7.5, "部分重叠"),
    ]

    pool = CandidatePool(
        domains=["wise.com", "paypal.com", "stripe.com"],
        by_domain={
            "wise.com": CandidateMeta("wise.com", "Wise", "https://wise.com"),
        },
    )
    result = run_cross_validate(
        _profile(),
        target_domain="airwallex.com",
        target_website_url="https://airwallex.com",
        pool=pool,
    )
    assert mock_fetch.call_count == 2
    assert mock_fetch.call_args_list[0].args[0] == ["airwallex.com"]
    assert mock_score.call_count == 1
    target_payload = mock_score.call_args[0][0]
    assert target_payload["title"] == "Airwallex"
    assert target_payload["company"] == "空中云汇"
    assert {s.domain for s in result.scores} == {"wise.com", "paypal.com", "stripe.com"}
    assert result.scores[0].domain == "wise.com"
    assert "airwallex.com" in result.heads


@patch("aperix_geo.services.competitor.cross_validate._score_batch")
@patch("aperix_geo.services.competitor.cross_validate.fetch_site_heads")
@patch("aperix_geo.services.competitor.cross_validate.get_settings")
def test_unreachable_hosts_skip_llm(mock_settings, mock_fetch, mock_score) -> None:
    mock_settings.return_value.competitor_pool_size = 50
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_settings.return_value.competitor_cross_validate_batch_size = 20
    mock_fetch.side_effect = [
        {"target.com": SiteHead("target.com", "Target", "主营", True)},
        {
            "good.com": SiteHead("good.com", "Good", "ok", True),
            "bad.com": SiteHead("bad.com", "", "", False),
        },
    ]
    mock_score.return_value = [CompetitorScore("good.com", 8.0, "竞品")]

    pool = CandidatePool(domains=["good.com", "bad.com"])
    result = run_cross_validate(
        {
            "company": "测试",
            "industry": "跨境药品",
            "features": "直购",
            "customers": "B2B",
            "search_queries": "跨境药品平台",
        },
        target_domain="target.com",
        pool=pool,
    )

    mock_score.assert_called_once()
    target_payload = mock_score.call_args[0][0]
    assert target_payload["title"] == "Target"
    payload = mock_score.call_args[0][1]
    assert len(payload) == 1
    assert payload[0]["domain"] == "good.com"
    bad = next(s for s in result.scores if s.domain == "bad.com")
    assert bad.score == 0.0
    assert "不可打开" in bad.reason


def test_candidate_payload_includes_seo_excerpt() -> None:
    head = SiteHead(
        "profound.ai",
        "Profound",
        "GEO platform",
        True,
        seo="type: website\nbrands: Profound\nschema: SoftwareApplication",
    )
    payload = _candidate_payload(head, None)
    assert payload["title"] == "Profound"
    assert "schema: SoftwareApplication" in payload["seo"]


def test_expand_ranked_only_passing_scores_sorted_desc() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("low.com", 6.0, "及格"),
            CompetitorScore("high.com", 9.0, "强竞品"),
            CompetitorScore("junk.com", 1.0, "无关"),
            CompetitorScore("mid.com", 7.5, "竞品"),
        ],
        heads={
            "low.com": SiteHead("low.com", "L", "d", True),
            "high.com": SiteHead("high.com", "H", "d", True),
            "junk.com": SiteHead("junk.com", "J", "d", True),
            "mid.com": SiteHead("mid.com", "M", "d", True),
        },
    )
    ordered = expand_ranked_domains(validation, min_score=6.0, max_keep=10)
    assert ordered == ["high.com", "mid.com", "low.com"]
    assert "junk.com" not in ordered


def test_expand_ranked_same_score_reachable_first() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("bad-high.com", 8.0, "打不开"),
            CompetitorScore("good.com", 8.0, "可打开"),
        ],
        heads={
            "bad-high.com": SiteHead("bad-high.com", "", "", False),
            "good.com": SiteHead("good.com", "Good", "ok", True),
        },
    )
    ordered = expand_ranked_domains(validation, min_score=6.0, max_keep=10)
    assert ordered == ["good.com", "bad-high.com"]
