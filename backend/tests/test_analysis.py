"""Tests for KPI aggregation from signal rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from aperix_geo.db.models import Competitor, LLMResponse, LLMResponseStatus, Subject, SubjectType
from aperix_geo.services.analysis.aggregate import aggregate_metrics, metrics_from_signals
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.utils.sentiment import NO_SENTIMENT_SCORE, persist_mention_rank
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft
from tests.parsed_fixtures import competitor_signal, entity_signal, parsed_payload, signal_rows_from_payload


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


def _signals_for_rows(rows: list[LLMResponse], subject: Subject, payloads: list[dict]) -> list[LLMResponseSignalRow]:
    return signal_rows_from_payload(rows, subject, parsed_payloads=payloads)


def test_aggregate_metrics_core_kpis():
    subject = _subject()
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2, mention_rank=1, has_domain_link=True, cited_on_source=True, sentiment_score=100.0),
            competitor_signal(mentioned=True, mention_count=1),
        ),
        parsed_payload(
            entity_signal(mentioned=True, mention_count=1, mention_rank=2, has_domain_link=True, cited_on_source=False, sentiment_score=50.0),
            competitor_signal(mentioned=True, mention_count=2),
        ),
        parsed_payload(competitor_signal(mentioned=False, mention_count=0)),
    ]
    rows = [_row(payload) for payload in payloads]
    all_signals = _signals_for_rows(rows, subject, payloads)
    own_signals = [row for row in all_signals if row.entity_id == OWN_ENTITY_ID]
    metrics = metrics_from_signals(own_signals, subject=subject, all_signals_for_voice=all_signals)
    assert metrics.response_count == 2
    assert metrics.visibility_rate == 1.0
    assert metrics.mention_rate == 1.5
    assert metrics.share_voice == round(3 / 6, 4)
    assert metrics.average_rank == 1.5
    assert metrics.citation_rate == 0.5
    assert metrics.sentiment_score == 75.0


def test_build_content_opportunities():
    from uuid import uuid4

    from aperix_geo.db.models import Competitor, Prompt
    from aperix_geo.services.analysis import build_content_opportunities

    subject = _subject()
    subject.competitors = [
        Competitor(id=uuid.uuid4(), subject_id=subject.id, brand="Beta", domain="")
    ]
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

    payloads = [
        parsed_payload(entity_signal(mentioned=False), competitor_signal(mentioned=True)),
        parsed_payload(entity_signal(mentioned=False, cited_on_source=False), competitor_signal(mentioned=True)),
    ]
    rows = [_row(payload) for payload in payloads]
    rows[0].prompt_id = prompt_id
    rows[0].platform = "deepseek"
    rows[1].prompt_id = prompt_id
    rows[1].platform = "deepseek"

    from datetime import UTC, datetime, timedelta

    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    signals = _signals_for_rows(rows, subject, payloads)
    original = load_llm_response_signals.override
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        out = build_content_opportunities(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        load_llm_response_signals.override = original

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
    from aperix_geo.services.analysis import _query as analysis_query
    from aperix_geo.services.analysis import build_backlink_opportunities
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

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

    payloads = [
        parsed_payload(entity_signal(cited_on_source=False), url_hosts=["support.google.com", "aperix.com"]),
        parsed_payload(entity_signal(cited_on_source=False), url_hosts=["support.google.com"]),
    ]
    rows = [_row(payload) for payload in payloads]
    rows[0].platform = "deepseek"
    rows[1].platform = "deepseek"
    rows[0].prompt_id = rows[1].prompt_id

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    signals = _signals_for_rows(rows, subject, payloads)
    own_signals = [row for row in signals if row.entity_id == OWN_ENTITY_ID]
    original_responses = analysis_query.responses_in_window.override
    original_signals = load_llm_response_signals.override
    analysis_query.responses_in_window.override = lambda *args, **kwargs: rows
    load_llm_response_signals.override = lambda *args, **kwargs: (
        own_signals if kwargs.get("entity_id") == OWN_ENTITY_ID else signals
    )
    try:
        out = build_backlink_opportunities(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        analysis_query.responses_in_window.override = original_responses
        load_llm_response_signals.override = original_signals

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
    from aperix_geo.services.analysis import build_diagnosis
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    subject = _subject()
    subject.competitors = [
        Competitor(id=uuid.uuid4(), subject_id=subject.id, brand="Beta", domain="")
    ]
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

    payloads = [
        parsed_payload(entity_signal(mentioned=False), competitor_signal(mentioned=True)),
        parsed_payload(entity_signal(mentioned=False), competitor_signal(mentioned=True)),
    ]
    rows = [_row(payload) for payload in payloads]
    for row in rows:
        row.prompt_id = prompt_id
        row.platform = "deepseek"

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    signals = _signals_for_rows(rows, subject, payloads)
    original = load_llm_response_signals.override
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        out = build_diagnosis(FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to)
    finally:
        load_llm_response_signals.override = original

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
    from aperix_geo.services.analysis._series import top_visibility_labels

    share = {f"Brand{i}": i / 100 for i in range(10)}
    share["Own"] = 0.01
    labels = top_visibility_labels(share, "Own", limit=5)
    assert "Own" in labels
    assert len(labels) == 5


def test_align_previous_daily_by_period_offset():
    from datetime import date

    from aperix_geo.services.analysis._series import align_previous_daily_to_current

    current = [
        {"date": "2026-05-02", "values": {"Own": 0.1}},
        {"date": "2026-05-04", "values": {"Own": 0.2}},
    ]
    previous = [
        {"date": "2026-04-02", "values": {"Own": 0.3}},
    ]
    aligned = align_previous_daily_to_current(
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
    subject.competitors = [
        Competitor(id=uuid.uuid4(), subject_id=subject.id, brand="Beta", domain="")
    ]

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

    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2),
            competitor_signal(mentioned=True, mention_count=1),
        ),
        parsed_payload(
            entity_signal(mentioned=False, mention_count=0),
            competitor_signal(mentioned=True, mention_count=3),
        ),
    ]
    rows = [_row(payload) for payload in payloads]
    rows[0].prompt_id = prompt_a
    rows[1].prompt_id = prompt_b

    from datetime import UTC, datetime, timedelta

    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    signals = _signals_for_rows(rows, subject, payloads)
    original = load_llm_response_signals.override
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        out = build_topic_visibility_ranks(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        load_llm_response_signals.override = original

    assert len(out) == 2
    assert out[0]["topic_name"] == "Topic A"
    assert out[0]["ranks"][0] == "aperix.com"
    assert out[1]["ranks"][0] == "Beta"


def _subject_with_competitor() -> Subject:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject.id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_metrics_from_signals_matches_core_kpis():
    subject = _subject_with_competitor()
    response_id = uuid.uuid4()
    created = datetime.now(UTC)
    own_row = LLMResponseSignalRow(
        response_id=response_id,
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        mentioned=True,
        mention_count=2,
        mention_rank=1,
        sentiment_score=80.0,
        sentiment_label="positive",
        has_domain_link=True,
        cited_on_source=True,
        created_at=created,
    )
    comp_row = LLMResponseSignalRow(
        response_id=response_id,
        subject_id=subject.id,
        prompt_id=own_row.prompt_id,
        platform="doubao",
        entity_id=str(subject.competitors[0].id),
        entity_kind="competitor",
        mentioned=True,
        mention_count=1,
        mention_rank=2,
        sentiment_score=55.0,
        sentiment_label="neutral",
        has_domain_link=False,
        cited_on_source=False,
        created_at=created,
    )
    all_signals = [own_row, comp_row]
    metrics = metrics_from_signals([own_row], subject=subject, all_signals_for_voice=all_signals)
    assert metrics.visibility_rate == 1.0
    assert metrics.mention_rate == 2.0
    assert metrics.share_voice == round(2 / 3, 4)
    assert metrics.citation_rate == 1.0
    assert metrics.sentiment_score == 80.0


def test_aggregate_metrics_entity_group():
    subject = _subject_with_competitor()
    response_id = uuid.uuid4()
    created = datetime.now(UTC)
    entity_signals = [
        EntitySignalDraft(
            entity_id=OWN_ENTITY_ID,
            entity_kind="own",
            entity_label="aperix.com",
            mentioned=True,
            mention_count=1,
            mention_rank=1,
        ),
        EntitySignalDraft(
            entity_id=str(subject.competitors[0].id),
            entity_kind="competitor",
            entity_label="beta.com",
            mentioned=False,
            mention_count=0,
        ),
    ]
    result = aggregate_metrics(
        [
            LLMResponseSignalRow(
                response_id=response_id,
                subject_id=subject.id,
                prompt_id=uuid.uuid4(),
                platform="doubao",
                entity_id=sig.entity_id,
                entity_kind=sig.entity_kind,
                mentioned=sig.mentioned,
                mention_count=sig.mention_count,
                mention_rank=persist_mention_rank(sig.mention_rank),
                sentiment_score=NO_SENTIMENT_SCORE,
                sentiment_label="neutral",
                has_domain_link=False,
                cited_on_source=False,
                created_at=created,
            )
            for sig in entity_signals
        ],
        subject=subject,
        group_by="entity",
    )
    assert len(result.rows) == 2
    own = next(row for row in result.rows if row["kind"] == "own")
    assert own["metrics"]["visibility_rate"] == 1.0
