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
    assert m.share_voice == round(3 / (3 + 3), 4)
    assert m.average_rank == round((1 + 2) / 2, 2)
    assert m.citation_rate == round(1 / 2, 4)
    assert m.sentiment_score == round((1.0 + 0.5) / 2, 4)


def test_empty_rows():
    m = compute_subject_metrics([], subject=_subject())
    assert m.response_count == 0
    assert m.visibility_rate is None
    assert m.mention_intensity is None


def test_rank_from_rows_visibility_share():
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitor_brands = []
    rows = [
        _row({"mentions_own": True}),
        _row({"mentions_own": False}),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["own_label"] == "Aperix"
    assert rank["visibility_share"]["Aperix"] == 0.5


def test_rank_from_rows_mention_share():
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitor_brands = []
    rows = [
        _row({"mentions_own": True, "mention_count_own": 2}),
        _row({"mentions_own": False, "mention_count_own": 0}),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["mention_share"]["Aperix"] == 1.0


def test_rank_from_rows_share_voice_and_average_rank():
    from aperix_geo.db.models import CompetitorBrand
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitor_brands = [CompetitorBrand(subject_id=subject.id, name="Beta")]
    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 3,
                "mention_counts_competitors": {"Beta": 1},
                "rank_own": 1,
                "rank_hints_first_index": {"Aperix": 0, "Beta": 50},
            }
        ),
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 1,
                "mention_counts_competitors": {"Beta": 2},
                "rank_own": 2,
                "rank_hints_first_index": {"Aperix": 10, "Beta": 0},
            }
        ),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["share_voice"]["Aperix"] == round(4 / (4 + 3), 4)
    assert rank["average_rank"]["Aperix"] == round((1 + 2) / 2, 2)


def test_rank_from_rows_citation_and_sentiment():
    from aperix_geo.db.models import CompetitorBrand
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitor_brands = [CompetitorBrand(subject_id=subject.id, name="Beta")]
    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 1,
                "mentions_competitors": {"Beta": True},
                "cited_own_domain": True,
                "sentiment_score_own": 0.8,
            }
        ),
        _row(
            {
                "mentions_own": False,
                "mentions_competitors": {"Beta": True},
            }
        ),
    ]
    rows[0].raw_text = "Aperix is great. Beta is bad."
    rows[1].raw_text = "Beta is recommended."

    rank = _rank_from_rows(rows, subject=subject)
    assert rank["citation_share"]["Aperix"] == 0.5
    assert rank["sentiment_score"]["Aperix"] == 0.8
    assert rank["sentiment_score"]["Beta"] is not None


def test_top_visibility_labels_keeps_own_brand():
    from aperix_geo.services.analysis import _top_visibility_labels

    share = {f"Brand{i}": i / 100 for i in range(10)}
    share["Own"] = 0.01
    labels = _top_visibility_labels(share, "Own", limit=5)
    assert "Own" in labels
    assert len(labels) == 5


def test_align_previous_daily_by_period_offset():
    from datetime import date

    from aperix_geo.services.analysis import _align_previous_daily_to_current

    current = [
        {"date": "2026-05-02", "values": {"Own": 0.1}},
        {"date": "2026-05-04", "values": {"Own": 0.2}},
    ]
    previous = [
        {"date": "2026-04-02", "values": {"Own": 0.3}},
    ]
    aligned = _align_previous_daily_to_current(
        current,
        previous,
        ["Own"],
        current_start=date(2026, 5, 1),
        previous_start=date(2026, 4, 1),
    )
    assert aligned[0]["values"]["Own"] == 0.3
    assert aligned[1]["values"]["Own"] == 0


def test_build_topic_visibility_ranks():
    import uuid

    from aperix_geo.db.models import CompetitorBrand, Prompt, Topic
    from aperix_geo.services.analysis import build_topic_visibility_ranks

    subject = _subject()
    topic_a = uuid.uuid4()
    topic_b = uuid.uuid4()
    prompt_a = uuid.uuid4()
    prompt_b = uuid.uuid4()
    subject.competitor_brands = [CompetitorBrand(subject_id=subject.id, name="Beta")]

    class FakeDb:
        def execute(self, stmt):
            class R:
                def scalars(self):
                    class S:
                        def all(self):
                            sql = str(stmt)
                            if "tb_prompts" in sql:
                                return [
                                    Prompt(id=prompt_a, subject_id=subject.id, topic_id=topic_a, text="p1"),
                                    Prompt(id=prompt_b, subject_id=subject.id, topic_id=topic_b, text="p2"),
                                ]
                            return [
                                Topic(id=topic_a, subject_id=subject.id, name="Topic A"),
                                Topic(id=topic_b, subject_id=subject.id, name="Topic B"),
                            ]

                    return S()

            return R()

    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 2,
                "mentions_competitors": {"Beta": True},
                "mention_counts_competitors": {"Beta": 1},
            }
        ),
        _row(
            {
                "mentions_own": False,
                "mention_count_own": 0,
                "mentions_competitors": {"Beta": True},
                "mention_counts_competitors": {"Beta": 3},
            }
        ),
    ]
    rows[0].prompt_id = prompt_a
    rows[1].prompt_id = prompt_b

    from datetime import UTC, datetime, timedelta

    from aperix_geo.services import analysis as analysis_mod

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = analysis_mod._responses_in_window
    analysis_mod._responses_in_window = lambda *args, **kwargs: rows
    try:
        out = build_topic_visibility_ranks(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        analysis_mod._responses_in_window = original

    assert len(out) == 2
    assert out[0]["topic_name"] == "Topic A"
    assert out[0]["ranks"][0] == "Aperix"
    assert out[1]["ranks"][0] == "Beta"
