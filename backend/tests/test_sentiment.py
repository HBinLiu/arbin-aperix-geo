"""Tests for ABSA → parsed sentiment mapping."""

from __future__ import annotations

from aperix_geo.services.sampling.sentiment import parsed_sentiment_from_absa
from aperix_geo.utils.sentiment import absa_score_to_label, absa_score_to_points


def test_absa_score_mapping() -> None:
    assert absa_score_to_points(1.0) == 100.0
    assert absa_score_to_points(0.0) == 50.0
    assert absa_score_to_points(-1.0) == 0.0
    assert absa_score_to_points(0.8) == 90.0
    assert absa_score_to_label(0.8) == "positive"
    assert absa_score_to_label(0.0) == "neutral"
    assert absa_score_to_label(-0.5) == "negative"


def test_parsed_sentiment_from_absa() -> None:
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {
                "mentioned": True,
                "score": 0.8,
                "framing_tags": ["稳定"],
                "evidence": "明确推荐 Aperix",
            },
            "Beta": {
                "mentioned": True,
                "score": 0.0,
                "framing_tags": [],
                "evidence": "客观对比 Beta",
            },
        },
    }
    result = parsed_sentiment_from_absa(
        response_absa,
        own_brand="Aperix",
        competitor_keys=[("Beta", "Beta")],
    )
    assert result["sentiment_source"] == "llm"
    assert result["sentiment_own"] == "positive"
    assert result["sentiment_score_own"] == 90.0
    assert result["sentiment_reason_own"] == "明确推荐 Aperix"
    assert result["sentiment_competitors"]["Beta"] == "neutral"
    assert result["sentiment_scores_competitors"]["Beta"] == 50.0
    assert result["sentiment_reasons_competitors"]["Beta"] == "客观对比 Beta"


def test_parsed_sentiment_from_absa_ignores_parser_mentions() -> None:
    """ABSA mention detection drives sentiment even when parser would miss the brand."""
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "阿里健康": {
                "mentioned": True,
                "score": 0.6,
                "framing_tags": [],
                "evidence": "阿里健康在医药电商领域表现突出",
            },
        },
    }
    result = parsed_sentiment_from_absa(
        response_absa,
        own_brand="阿里健康",
        competitor_keys=[],
    )
    assert result["sentiment_own"] == "positive"
    assert result["sentiment_score_own"] == 80.0


def test_parsed_sentiment_from_absa_not_mentioned() -> None:
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": False, "score": 0.9, "framing_tags": [], "evidence": ""},
        },
    }
    result = parsed_sentiment_from_absa(
        response_absa,
        own_brand="Aperix",
        competitor_keys=[],
    )
    assert result["sentiment_own"] == "neutral"
    assert result["sentiment_score_own"] is None


def test_parsed_sentiment_from_absa_failed() -> None:
    result = parsed_sentiment_from_absa(
        {"analysis_source": "failed"},
        own_brand="Aperix",
        competitor_keys=[],
    )
    assert result["sentiment_source"] == "failed"
    assert result["sentiment_score_own"] is None
