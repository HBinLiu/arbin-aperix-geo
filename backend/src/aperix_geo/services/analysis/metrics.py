"""KPI metric bundle returned by signal aggregation."""

from __future__ import annotations

from dataclasses import dataclass


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
