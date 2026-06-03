"""Competitor list: min score gate and score-desc ordering."""

from aperix_geo.services.competitor.cross_validate import expand_ranked_domains
from aperix_geo.services.competitor.types import CompetitorScore, CrossValidateResult, SiteHead


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
