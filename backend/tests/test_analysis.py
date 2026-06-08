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
                "has_own_domain_link": True,
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
                "has_own_domain_link": True,
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
    assert m.mention_rate == round(3 / 3, 4)
    assert m.share_voice == round(3 / (3 + 3), 4)
    assert m.average_rank == round((1 + 2) / 2, 2)
    assert m.citation_rate == round(1 / 2, 4)
    assert m.sentiment_score == 75.0


def test_empty_rows():
    m = compute_subject_metrics([], subject=_subject())
    assert m.response_count == 0
    assert m.visibility_rate is None
    assert m.mention_rate is None


def test_rank_from_rows_visibility_share():
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitors = []
    rows = [
        _row({"mentions_own": True}),
        _row({"mentions_own": False}),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["own_label"] == "aperix.com"
    assert rank["visibility_share"]["aperix.com"] == 0.5


def test_rank_from_rows_mention_rate():
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitors = []
    rows = [
        _row({"mentions_own": True, "mention_count_own": 2}),
        _row({"mentions_own": False, "mention_count_own": 0}),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["mention_rate"]["aperix.com"] == 1.0


def test_rank_from_rows_share_voice_and_average_rank():
    from aperix_geo.db.models import Competitor
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitors = [Competitor(subject_id=subject.id, brand="Beta", domain="")]
    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 3,
                "mention_counts_competitors": {"Beta": 1},
                "rank_own": 1,
                "rank_hints_first_index": {"aperix.com": 0, "Beta": 50},
            }
        ),
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 1,
                "mention_counts_competitors": {"Beta": 2},
                "rank_own": 2,
                "rank_hints_first_index": {"aperix.com": 10, "Beta": 0},
            }
        ),
    ]
    rank = _rank_from_rows(rows, subject=subject)
    assert rank["share_voice"]["aperix.com"] == round(4 / (4 + 3), 4)
    assert rank["average_rank"]["aperix.com"] == round((1 + 2) / 2, 2)


def test_rank_from_rows_citation_and_sentiment():
    from aperix_geo.db.models import Competitor
    from aperix_geo.services.analysis import _rank_from_rows

    subject = _subject()
    subject.competitors = [Competitor(subject_id=subject.id, brand="Beta", domain="")]
    rows = [
        _row(
            {
                "mentions_own": True,
                "mention_count_own": 1,
                "mentions_competitors": {"Beta": True},
                "cited_own_domain": True,
                "sentiment_score_own": 80,
                "sentiment_scores_competitors": {"Beta": 20},
            }
        ),
        _row(
            {
                "mentions_own": False,
                "mentions_competitors": {"Beta": True},
                "sentiment_scores_competitors": {"Beta": 90},
            }
        ),
    ]
    rows[0].raw_text = "Aperix is great. Beta is bad."
    rows[1].raw_text = "Beta is recommended."

    rank = _rank_from_rows(rows, subject=subject)
    assert rank["citation_share"]["aperix.com"] == 0.5
    assert rank["sentiment_score"]["aperix.com"] == 80.0
    assert rank["sentiment_score"]["Beta"] == 55.0


def test_build_content_opportunities():
    from uuid import uuid4

    from aperix_geo.db.models import Competitor, Prompt
    from aperix_geo.services.analysis import build_content_opportunities

    subject = _subject()
    subject.competitors = [Competitor(subject_id=subject.id, brand="Beta", domain="")]
    prompt_id = uuid4()
    prompt = Prompt(id=prompt_id, subject_id=subject.id, topic_id=uuid4(), text="AI 搜索关键词")

    class FakeDb:
        def execute(self, stmt):
            class R:
                def scalars(self):
                    class S:
                        def all(self):
                            sql = str(stmt)
                            if "tb_prompts" in sql:
                                return [prompt]
                            return []

                    return S()

            return R()

        def get(self, _model, _id):
            return subject

    rows = [
        _row({"mentions_own": False, "mentions_competitors": {"Beta": True}}),
        _row({"mentions_own": False, "mentions_competitors": {"Beta": True}, "cited_own_domain": False}),
    ]
    rows[0].prompt_id = prompt_id
    rows[0].platform = "deepseek"
    rows[1].prompt_id = prompt_id
    rows[1].platform = "deepseek"

    from datetime import UTC, datetime, timedelta

    from aperix_geo.services import analysis as analysis_mod

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = analysis_mod._responses_in_window.override
    analysis_mod._responses_in_window.override = lambda *args, **kwargs: rows
    try:
        out = build_content_opportunities(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        analysis_mod._responses_in_window.override = original

    assert len(out["items"]) == 1
    item = out["items"][0]
    assert item["brand_gap_rate"] == 1.0
    assert item["brand_own_count"] == 0
    assert item["brand_total_count"] == 2
    assert item["priority"] == "high"
    assert "Beta" in item["competitors"]


def test_build_backlink_opportunities():
    from datetime import UTC, datetime, timedelta

    from aperix_geo.db.models import Competitor
    from aperix_geo.services import analysis as analysis_mod
    from aperix_geo.services.analysis import build_backlink_opportunities

    subject = _subject()
    subject.competitors = [
        Competitor(
            subject_id=subject.id,
            domain="beta.com",
            website_url="https://beta.com",
            brand="Beta",
        )
    ]

    class FakeDb:
        def execute(self, stmt):
            class R:
                def scalars(self):
                    class S:
                        def all(self):
                            return ["beta.com"]

                        def __iter__(self):
                            return iter(self.all())

                    return S()

            return R()

    rows = [
        _row(
            {
                "cited_own_domain": False,
                "url_hosts": ["support.google.com", "aperix.com"],
            }
        ),
        _row(
            {
                "cited_own_domain": False,
                "url_hosts": ["support.google.com"],
            }
        ),
    ]
    rows[0].platform = "deepseek"
    rows[1].platform = "deepseek"
    rows[0].prompt_id = rows[1].prompt_id

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = analysis_mod._responses_in_window.override
    analysis_mod._responses_in_window.override = lambda *args, **kwargs: rows
    try:
        out = build_backlink_opportunities(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        analysis_mod._responses_in_window.override = original

    assert len(out["items"]) == 1
    item = out["items"][0]
    assert item["host"] == "support.google.com"
    assert item["platform"] == "deepseek"
    assert item["chat_count"] == 2
    assert item["prompt_count"] == 1
    assert item["domain_type"] == "other"


def test_build_diagnosis():
    from datetime import timedelta
    from uuid import uuid4

    from aperix_geo.db.models import Competitor, Prompt
    from aperix_geo.services import analysis as analysis_mod
    from aperix_geo.services.analysis import build_diagnosis

    subject = _subject()
    subject.competitors = [Competitor(subject_id=subject.id, brand="Beta", domain="")]
    prompt_id = uuid4()
    prompt = Prompt(id=prompt_id, subject_id=subject.id, topic_id=uuid4(), text="追踪AI搜索推荐流量的工具推荐")

    class FakeDb:
        def execute(self, stmt):
            class R:
                def scalars(self):
                    class S:
                        def all(self):
                            sql = str(stmt)
                            if "tb_prompts" in sql:
                                return [prompt]
                            return []

                    return S()

            return R()

    rows = [
        _row({"mentions_own": False, "mentions_competitors": {"Beta": True}}),
        _row({"mentions_own": False, "mentions_competitors": {"Beta": True}}),
    ]
    for row in rows:
        row.prompt_id = prompt_id
        row.platform = "deepseek"

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = analysis_mod._responses_in_window.override
    analysis_mod._responses_in_window.override = lambda *args, **kwargs: rows
    try:
        out = build_diagnosis(FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to)
    finally:
        analysis_mod._responses_in_window.override = original

    assert "overall_score" in out
    assert out["overall_status"] in {"excellent", "good", "needs_improvement", "critical"}
    assert out["dimensions"]["mention"]["health_score"] >= 0
    assert out["dimensions"]["prompt"]["health_score"] >= 0
    assert len(out["mention_items"]) == 1
    assert len(out["prompt_items"]) == 1

    mention = out["mention_items"][0]
    assert mention["prompt_text"] == prompt.text
    assert mention["platform"] == "deepseek"
    assert mention["mention_rate"] == 0
    assert mention["mention_own_count"] == 0
    assert mention["mention_total_count"] == 2
    assert mention["issue_type"] == "not_mentioned"
    assert "Beta" in mention["competitors"]

    prompt_item = out["prompt_items"][0]
    assert prompt_item["prompt_id"] == str(prompt_id)
    assert prompt_item["priority"] == "high"
    assert "search_volume" not in prompt_item


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

    from aperix_geo.db.models import Competitor, Prompt, Topic
    from aperix_geo.services.analysis import build_topic_visibility_ranks

    subject = _subject()
    topic_a = uuid.uuid4()
    topic_b = uuid.uuid4()
    prompt_a = uuid.uuid4()
    prompt_b = uuid.uuid4()
    subject.competitors = [Competitor(subject_id=subject.id, brand="Beta", domain="")]

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
    original = analysis_mod._responses_in_window.override
    analysis_mod._responses_in_window.override = lambda *args, **kwargs: rows
    try:
        out = build_topic_visibility_ranks(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        analysis_mod._responses_in_window.override = original

    assert len(out) == 2
    assert out[0]["topic_name"] == "Topic A"
    assert out[0]["ranks"][0] == "aperix.com"
    assert out[1]["ranks"][0] == "Beta"
