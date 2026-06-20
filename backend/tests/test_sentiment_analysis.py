"""Tests for sentiment analysis page payload."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject, SubjectType
from aperix_geo.services.analysis.aggregate import daily_sentiment_distribution_from_signals
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from tests.parsed_fixtures import entity_signal, parsed_payload, signal_rows_from_payload


def _subject() -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
        sampling_platforms=["doubao", "deepseek"],
    )


def _signal_row(
    *,
    platform: str = "doubao",
    day: datetime | None = None,
    sentiment_score: float = 80.0,
) -> LLMResponseSignalRow:
    subject = _subject()
    response = LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform=platform,
        status=LLMResponseStatus.success,
        parsed=parsed_payload(
            entity_signal(mentioned=True, sentiment_score=sentiment_score),
        ),
        created_at=day or datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    return signal_rows_from_payload([response], subject, parsed_payloads=[response.parsed])[0]


def test_daily_sentiment_distribution_includes_platform_scores():
    day = datetime(2026, 6, 1, tzinfo=UTC)
    signals = [
        _signal_row(platform="doubao", day=day, sentiment_score=80.0),
        _signal_row(platform="deepseek", day=day, sentiment_score=60.0),
    ]

    series = daily_sentiment_distribution_from_signals(
        signals,
        entity_id=OWN_ENTITY_ID,
        platform_ids=["doubao", "deepseek"],
    )

    assert len(series) == 1
    point = series[0]
    assert point["date"] == "2026-06-01"
    assert point["platform_scores"]["doubao"] == 80.0
    assert point["platform_scores"]["deepseek"] == 60.0
    assert point["sentiment_score"] == 70.0
    assert point["sentiment_label"] == "neutral"


def test_daily_sentiment_distribution_omits_platform_scores_without_ids():
    signals = [_signal_row()]

    series = daily_sentiment_distribution_from_signals(signals, entity_id=OWN_ENTITY_ID)

    assert "platform_scores" not in series[0]
