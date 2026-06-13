"""Tests for competitor search quality gate."""

from aperix_geo.services.competitor.cross_validate import (
    QUALITY_STOP_AVG_OFFSET,
    CompetitorScore,
    competitor_quality_met,
)
from aperix_geo.services.competitor.types import CrossValidateResult, SiteHead

_PASS = 6.0


def test_competitor_quality_met_requires_count_and_avg() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("a.com", 8.0, "强竞品"),
            CompetitorScore("b.com", 7.0, "强竞品"),
            CompetitorScore("c.com", 6.5, "及格"),
        ],
        heads={
            "a.com": SiteHead("a.com", "A", "", True),
            "b.com": SiteHead("b.com", "B", "", True),
            "c.com": SiteHead("c.com", "C", "", True),
        },
    )
    assert competitor_quality_met(validation, pass_score=_PASS, min_count=3)


def test_competitor_quality_met_rejects_low_avg() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("a.com", 6.1, "勉强"),
            CompetitorScore("b.com", 6.0, "勉强"),
            CompetitorScore("c.com", 6.2, "勉强"),
        ],
        heads={
            "a.com": SiteHead("a.com", "A", "", True),
            "b.com": SiteHead("b.com", "B", "", True),
            "c.com": SiteHead("c.com", "C", "", True),
        },
    )
    assert not competitor_quality_met(validation, pass_score=_PASS, min_count=3)


def test_competitor_quality_met_ignores_unreachable() -> None:
    validation = CrossValidateResult(
        scores=[
            CompetitorScore("a.com", 9.0, "强"),
            CompetitorScore("b.com", 8.0, "强"),
            CompetitorScore("c.com", 7.0, "不可达"),
        ],
        heads={
            "a.com": SiteHead("a.com", "A", "", True),
            "b.com": SiteHead("b.com", "B", "", True),
            "c.com": SiteHead("c.com", "C", "", False),
        },
    )
    assert not competitor_quality_met(validation, pass_score=_PASS, min_count=3)


def test_quality_stop_avg_offset() -> None:
    assert QUALITY_STOP_AVG_OFFSET == 0.5
