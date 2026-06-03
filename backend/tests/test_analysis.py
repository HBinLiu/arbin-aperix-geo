"""Tests for compute_subject_metrics and KPI aggregation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject, SubjectType
from aperix_geo.services.analysis import compute_subject_metrics


def _subject() -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


def _row(parsed: dict) -> LLMResponse:
    return LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform="deepseek",
        status=LLMResponseStatus.success,
        parsed=parsed,
        created_at=datetime.now(UTC),
    )


def test_compute_subject_metrics_six_kpis():
    subject = _subject()
    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 2,
                "mention_counts_competitors": {"Beta": 1},
                "rank_own": 1,
                "cited_own_domain": True,
                "sentiment_score_own": 1.0,
            }
        ),
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 1,
                "mention_counts_competitors": {"Beta": 2},
                "rank_own": 2,
                "cited_own_domain": False,
                "sentiment_score_own": 0.5,
            }
        ),
        _row(
            {
                "mentions_own": False,
                "mention_count_own": 0,
                "mention_counts_competitors": {"Beta": 0},
            }
        ),
    ]
    m = compute_subject_metrics(rows, subject=subject)
    assert m.response_count == 3
    assert m.visibility_rate == round(2 / 3, 4)
    assert m.mention_intensity == round(3 / 3, 4)
    assert m.share_of_voice == round(3 / (3 + 3), 4)
    assert m.average_rank == round((1 + 2) / 2, 2)
    assert m.citation_rate == round(1 / 2, 4)
    assert m.sentiment_score == round((1.0 + 0.5) / 2, 4)


def test_empty_rows():
    m = compute_subject_metrics([], subject=_subject())
    assert m.response_count == 0
    assert m.visibility_rate is None
    assert m.mention_intensity is None
