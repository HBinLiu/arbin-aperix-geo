"""Map citation response ABSA to parsed sampling sentiment fields."""

from __future__ import annotations

from typing import Any

from aperix_geo.utils.sentiment import absa_score_to_label, absa_score_to_points


def _empty_result(*, sentiment_source: str) -> dict[str, Any]:
    return {
        "sentiment_own": "neutral",
        "sentiment_score_own": None,
        "sentiment_reason_own": None,
        "sentiment_competitors": {},
        "sentiment_scores_competitors": {},
        "sentiment_reasons_competitors": {},
        "sentiment_source": sentiment_source,
    }


def _absa_brand_entry(entry: Any) -> tuple[str, float | None, str | None]:
    if not isinstance(entry, dict) or entry.get("mentioned") is False:
        return "neutral", None, None
    score_raw = entry.get("score")
    try:
        absa_score = float(score_raw) if score_raw is not None else None
    except (TypeError, ValueError):
        absa_score = None
    if absa_score is None:
        return "neutral", None, None
    label = absa_score_to_label(absa_score)
    points = absa_score_to_points(absa_score)
    reason = str(entry.get("evidence") or "").strip() or None
    return label, points, reason


def parsed_sentiment_from_absa(
    response_absa: dict[str, Any],
    *,
    own_brand: str,
    competitor_keys: list[tuple[str, str]],
    mentions_own: bool,
    mentions_competitors: dict[str, bool],
) -> dict[str, Any]:
    """Convert response-level ABSA output to legacy parsed sentiment fields."""
    if response_absa.get("analysis_source") == "failed":
        return _empty_result(sentiment_source="failed")

    brands = response_absa.get("brands_sentiment_absa")
    if not isinstance(brands, dict):
        return _empty_result(sentiment_source="failed")

    sentiment_own = "neutral"
    sentiment_score_own: float | None = None
    sentiment_reason_own: str | None = None
    if mentions_own:
        sentiment_own, sentiment_score_own, sentiment_reason_own = _absa_brand_entry(brands.get(own_brand))

    sentiment_competitors: dict[str, str] = {}
    sentiment_scores_competitors: dict[str, float] = {}
    sentiment_reasons_competitors: dict[str, str] = {}
    for absa_key, output_label in competitor_keys:
        if not mentions_competitors.get(output_label):
            continue
        label, score, reason = _absa_brand_entry(brands.get(absa_key))
        if score is None:
            continue
        sentiment_competitors[output_label] = label
        sentiment_scores_competitors[output_label] = score
        if reason:
            sentiment_reasons_competitors[output_label] = reason

    return {
        "sentiment_own": sentiment_own,
        "sentiment_score_own": sentiment_score_own,
        "sentiment_reason_own": sentiment_reason_own,
        "sentiment_competitors": sentiment_competitors,
        "sentiment_scores_competitors": sentiment_scores_competitors,
        "sentiment_reasons_competitors": sentiment_reasons_competitors,
        "sentiment_source": "llm",
    }
