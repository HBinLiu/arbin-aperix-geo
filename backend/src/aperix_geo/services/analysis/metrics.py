"""Core KPI metrics from parsed response rows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from aperix_geo.db.models import LLMResponse, Subject, SubjectType
from aperix_geo.services.analysis._parsed import (
    avg_sentiment_points,
    has_own_domain_link,
    mentions_own,
    parsed_sentiment_score,
)
from aperix_geo.utils.coerce import safe_int


@dataclass
class MetricsBundle:
    response_count: int
    visibility_rate: float | None
    mention_rate: float | None
    share_voice: float | None
    average_rank: float | None
    citation_rate: float | None
    sentiment_score: float | None
    sentiment_count: dict[str, int]
    citation_coverage: float | None


def compute_subject_metrics(rows: list[LLMResponse], *, subject: Subject) -> MetricsBundle:
    """Compute the six core KPIs from parsed response rows."""
    n = len(rows)
    if n == 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_rate=None,
            share_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_count={"positive": 0, "neutral": 0, "negative": 0},
            citation_coverage=None,
        )

    mention_rows = 0
    mention_count_total = 0
    competitor_voice_total = 0
    ranks: list[float] = []
    own_domain_link_rows = 0
    cited_on_source_rows = 0
    sentiment_scores: list[float] = []
    sentiment_count: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    cited_all = 0

    for r in rows:
        p = r.parsed or {}
        if mentions_own(p):
            mention_rows += 1
            score = parsed_sentiment_score(p)
            if score is not None:
                sentiment_scores.append(score)
            label = p.get("sentiment_own") or "neutral"
            if label not in sentiment_count:
                label = "neutral"
            sentiment_count[label] += 1

        if has_own_domain_link(p):
            own_domain_link_rows += 1
            if p.get("cited_own_domain"):
                cited_on_source_rows += 1

        mc_own = safe_int(p, "mention_count_own")
        if mc_own == 0 and mentions_own(p):
            mc_own = 1
        mention_count_total += mc_own

        comp_counts = p.get("mention_counts_competitors") or {}
        if isinstance(comp_counts, dict):
            competitor_voice_total += sum(int(v) for v in comp_counts.values() if v)

        rank = p.get("rank_own")
        if rank is not None:
            try:
                ranks.append(float(rank))
            except (TypeError, ValueError):
                pass

        if p.get("cited_own_domain"):
            cited_all += 1

    total_voice = mention_count_total + competitor_voice_total
    return MetricsBundle(
        response_count=n,
        visibility_rate=round(mention_rows / n, 4),
        mention_rate=round(mention_count_total / n, 4),
        share_voice=round(mention_count_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        citation_rate=round(cited_on_source_rows / own_domain_link_rows, 4)
        if own_domain_link_rows > 0
        else None,
        sentiment_score=avg_sentiment_points(sentiment_scores),
        sentiment_count=sentiment_count,
        citation_coverage=round(cited_all / n, 4)
        if subject.type == SubjectType.domain or subject.website_url
        else None,
    )


def platform_metrics_from_rows(
    rows_by_platform: dict[str, list[LLMResponse]],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for platform, prows in rows_by_platform.items():
        metrics = compute_subject_metrics(prows, subject=subject)
        out.append(
            {
                "platform": platform,
                "visibility_rate": metrics.visibility_rate,
                "share_voice": metrics.share_voice,
                "citation_rate": metrics.citation_rate,
                "average_rank": metrics.average_rank,
                "sentiment_score": metrics.sentiment_score,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


def daily_platform_metric_series(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    field: str,
) -> list[dict[str, Any]]:
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)
    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        metrics = compute_subject_metrics(by_date[day], subject=subject)
        series.append({"date": day.isoformat(), "value": getattr(metrics, field)})
    return series
