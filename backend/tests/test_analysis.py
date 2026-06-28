"""Tests for KPI aggregation from signal rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from aperix_geo.db.models import Competitor, LLMResponse, LLMResponseStatus, Subject, SubjectType
from aperix_geo.services.analysis.aggregate import aggregate_metrics, mentioned_brands_for_response, metrics_from_signals
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, list_analysis_entities
from aperix_geo.utils.mention import persist_mention_rank
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
    assert metrics.citation_rate == 1.0
    assert metrics.sentiment_score == 75.0


def test_citation_rate_mention_with_domain_link_ratio():
    subject = _subject()
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=1, has_domain_link=True),
        ),
        parsed_payload(
            entity_signal(mentioned=True, mention_count=1, has_domain_link=False),
        ),
        parsed_payload(
            entity_signal(mentioned=False, mention_count=0, has_domain_link=True),
        ),
    ]
    rows = [_row(payload) for payload in payloads]
    all_signals = _signals_for_rows(rows, subject, payloads)
    own_signals = [row for row in all_signals if row.entity_id == OWN_ENTITY_ID]
    metrics = metrics_from_signals(own_signals, subject=subject)
    assert metrics.citation_rate == 0.5


def test_gap_priority():
    from aperix_geo.services.analysis.diagnosis_rules import (
        gap_action_priority,
        mention_action_priority,
        overall_action_priority,
    )

    assert gap_action_priority(0.0) == "low"
    assert gap_action_priority(0.49) == "low"
    assert gap_action_priority(0.5) == "medium"
    assert gap_action_priority(0.79) == "medium"
    assert gap_action_priority(0.8) == "high"
    assert gap_action_priority(1.0) == "high"


def test_action_priority_standards():
    from aperix_geo.services.analysis.diagnosis_rules import (
        gap_action_priority,
        mention_action_priority,
        overall_action_priority,
    )

    assert mention_action_priority(0.0, None) == "high"
    assert mention_action_priority(0.3, None) == "medium"
    assert mention_action_priority(0.6, 4.0) == "medium"
    assert mention_action_priority(0.6, 2.0) == "low"

    assert overall_action_priority("low", "medium", "low") == "medium"
    assert overall_action_priority("high", "medium", "low") == "high"
    assert gap_action_priority(0.75) == "medium"


def test_diagnosis_gap_metrics():
    from uuid import uuid4

    from aperix_geo.db.models import Competitor
    from aperix_geo.services.analysis.prompt_detail import _diagnosis_gap_metrics as diagnosis_gap_metrics

    subject = _subject()
    comp_id = uuid4()
    subject.competitors = [
        Competitor(id=comp_id, subject_id=subject.id, brand="Beta", domain="beta.com")
    ]

    r1, r2, r3 = uuid4(), uuid4(), uuid4()
    signals = [
        _signal(r1, "own", mentioned=True),
        _signal(r2, "own", mentioned=False),
        _signal(r3, "own", mentioned=True),
        _signal(r1, str(comp_id), mentioned=True),
        _signal(r2, str(comp_id), mentioned=True),
        _signal(r3, str(comp_id), mentioned=False),
    ]

    gap = diagnosis_gap_metrics(
        focus_entity_id="own",
        response_ids={r1, r2, r3},
        all_signals=signals,
        subject=subject,
    )
    assert gap["brand_gap_rate"] == 0.5
    assert gap["brand_own_count"] == 1
    assert gap["brand_total_count"] == 2

    gap_behind = diagnosis_gap_metrics(
        focus_entity_id="own",
        response_ids={r1, r2},
        all_signals=signals,
        subject=subject,
    )
    assert gap_behind["brand_gap_rate"] == 0.5
    assert gap_behind["brand_own_count"] == 1
    assert gap_behind["brand_total_count"] == 2
    assert gap_behind["brand_gap_priority"] == "medium"
    assert gap_behind["competitors"] == ["beta.com"]


def _signal(
    response_id,
    entity_id: str,
    *,
    mentioned: bool,
    cited_on_source: bool = False,
    has_domain_link: bool = False,
):
    from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow

    return LLMResponseSignalRow(
        response_id=response_id,
        subject_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform="deepseek",
        entity_id=entity_id,
        entity_kind="own" if entity_id == "own" else "competitor",
        brand_id=uuid.uuid4(),
        mentioned=mentioned,
        mention_count=1 if mentioned else 0,
        mention_rank=1 if mentioned else 0,
        sentiment_score=0.0,
        sentiment_reason="",
        has_domain_link=has_domain_link,
        cited_on_source=cited_on_source,
        created_at=datetime.now(UTC),
    )


def test_diagnosis_gap_metrics_source_domain_link():
    from uuid import uuid4

    from aperix_geo.db.models import Competitor
    from aperix_geo.services.analysis.prompt_detail import _diagnosis_gap_metrics as diagnosis_gap_metrics

    subject = _subject()
    comp_id = uuid4()
    subject.competitors = [
        Competitor(id=comp_id, subject_id=subject.id, brand="Beta", domain="beta.com")
    ]

    r1, r2 = uuid4(), uuid4()
    signals = [
        _signal(r1, "own", mentioned=True, has_domain_link=False),
        _signal(r2, "own", mentioned=True, has_domain_link=False),
        _signal(r1, str(comp_id), mentioned=True, has_domain_link=True),
        _signal(r2, str(comp_id), mentioned=False, has_domain_link=True),
    ]

    gap = diagnosis_gap_metrics(
        focus_entity_id="own",
        response_ids={r1, r2},
        all_signals=signals,
        subject=subject,
    )
    assert gap["source_gap_rate"] == 1.0
    assert gap["source_own_count"] == 0
    assert gap["source_total_count"] == 2


def test_diagnosis_gap_health_uses_gap_prompts_only():
    """Gap health scores average only prompts with positive gap rate."""
    from aperix_geo.services.analysis.diagnosis_rules import health_score_from_gap_items

    gap_items = [
        {"brand_gap_rate": 0.0, "source_gap_rate": 0.0},
        {"brand_gap_rate": 0.8, "source_gap_rate": 0.6},
    ]

    assert health_score_from_gap_items(gap_items, gap_key="brand_gap_rate") == 20.0
    assert health_score_from_gap_items(gap_items, gap_key="source_gap_rate") == 40.0


def test_build_backlink_opportunities():
    from datetime import UTC, datetime, timedelta

    from aperix_geo.db.models import Competitor
    from aperix_geo.services.analysis import build_backlink_opportunities
    from aperix_geo.services.analysis.backlink_sql import _query_backlink_domain_stats

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
        pass

    stats_items = [
        {
            "id": "google.com",
            "domain": "google.com",
            "platforms": ["deepseek"],
            "priority": "medium",
            "citation_count": 2,
            "prompt_count": 1,
            "chat_count": 2,
        }
    ]

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = _query_backlink_domain_stats.override
    _query_backlink_domain_stats.override = lambda *args, **kwargs: stats_items
    try:
        out = build_backlink_opportunities(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        _query_backlink_domain_stats.override = original

    assert out["total"] == 1
    assert out["page"] == 1
    assert out["page_size"] == 10
    assert len(out["items"]) == 1
    item = out["items"][0]
    assert item["domain"] == "google.com"
    assert item["platforms"] == ["deepseek"]
    assert item["citation_count"] == 2
    assert item["chat_count"] == 2
    assert item["prompt_count"] == 1


def test_build_backlink_opportunities_groups_by_host():
    from datetime import UTC, datetime, timedelta

    from aperix_geo.services.analysis import build_backlink_opportunities
    from aperix_geo.services.analysis.backlink_sql import _query_backlink_domain_stats

    subject = _subject()
    stats_items = [
        {
            "id": "google.com",
            "domain": "google.com",
            "platforms": ["chatgpt", "deepseek"],
            "priority": "medium",
            "citation_count": 2,
            "prompt_count": 1,
            "chat_count": 2,
        }
    ]

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = _query_backlink_domain_stats.override
    _query_backlink_domain_stats.override = lambda *args, **kwargs: stats_items
    try:
        out = build_backlink_opportunities(
            object(),
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
        )
    finally:
        _query_backlink_domain_stats.override = original

    assert out["total"] == 1
    item = out["items"][0]
    assert item["domain"] == "google.com"
    assert item["platforms"] == ["chatgpt", "deepseek"]
    assert item["chat_count"] == 2
    assert item["prompt_count"] == 1


def test_build_backlink_opportunities_search_and_pagination():
    from datetime import UTC, datetime, timedelta

    from aperix_geo.services.analysis import build_backlink_opportunities
    from aperix_geo.services.analysis.backlink_sql import _query_backlink_domain_stats

    subject = _subject()
    stats_items = [
        {
            "id": "alpha.example.com",
            "domain": "alpha.example.com",
            "platforms": ["deepseek"],
            "priority": "low",
            "citation_count": 1,
            "prompt_count": 1,
            "chat_count": 1,
        },
        {
            "id": "beta.example.com",
            "domain": "beta.example.com",
            "platforms": ["deepseek"],
            "priority": "low",
            "citation_count": 1,
            "prompt_count": 1,
            "chat_count": 1,
        },
    ]

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = _query_backlink_domain_stats.override
    _query_backlink_domain_stats.override = lambda *args, **kwargs: stats_items
    try:
        filtered = build_backlink_opportunities(
            object(),
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            search="alpha",
        )
        paged = build_backlink_opportunities(
            object(),
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            page=1,
            page_size=1,
            sort_by="chat_count",
            order="desc",
        )
    finally:
        _query_backlink_domain_stats.override = original

    assert filtered["total"] == 1
    assert filtered["items"][0]["domain"] == "alpha.example.com"
    assert paged["total"] == 2
    assert len(paged["items"]) == 1


def test_build_backlink_opportunity_detail():
    from datetime import UTC, datetime, timedelta

    from aperix_geo.services.analysis import build_backlink_opportunity_detail
    from aperix_geo.services.analysis.backlink_sql import _BacklinkDomainContext, _query_backlink_domain_context

    subject = _subject()
    ctx = _BacklinkDomainContext(
        domain="yahoo.com",
        citation_count=3,
        chat_count=2,
        prompt_count=2,
        platforms=["chatgpt", "deepseek"],
    )

    class FakeDb:
        def execute(self, _stmt):
            class R:
                def all(self):
                    return []

                def scalars(self):
                    class S:
                        def all(self):
                            return []

                    return S()

            return R()

        def scalar(self, _stmt):
            return 100

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    original = _query_backlink_domain_context.override
    _query_backlink_domain_context.override = lambda *args, **kwargs: ctx
    try:
        out = build_backlink_opportunity_detail(
            FakeDb(),
            subject=subject,
            domain="yahoo.com",
            dt_from=dt_from,
            dt_to=dt_to,
        )
    finally:
        _query_backlink_domain_context.override = original

    assert out["domain"] == "yahoo.com"
    assert out["citation_count"] == 3
    assert out["chat_count"] == 2
    assert out["prompt_count"] == 2
    assert out["platforms"] == ["chatgpt", "deepseek"]
    assert out["citation_rate"] == 0.02


def test_top_visibility_labels_keeps_own_brand():
    from aperix_geo.services.analysis._series import top_visibility_labels

    share = {f"Brand{i}": i / 100 for i in range(10)}
    share["Own"] = 0.01
    labels = top_visibility_labels(share, "Own", limit=5)
    assert "Own" in labels
    assert len(labels) == 5

    all_labels = top_visibility_labels(share, "Own", limit=None)
    assert len(all_labels) == len(share)


def test_build_dual_signal_window_splits_once():
    from datetime import datetime, timezone
    from uuid import uuid4

    from aperix_geo.services.analysis.signal_index import build_dual_signal_window
    from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow

    subject_id = uuid4()
    prompt_id = uuid4()
    brand_id = uuid4()
    dt_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
    dt_to = datetime(2026, 5, 7, tzinfo=timezone.utc)
    prev_from = datetime(2026, 4, 24, tzinfo=timezone.utc)
    prev_to = datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc)

    def row(day: int, entity_id: str = "own") -> LLMResponseSignalRow:
        return LLMResponseSignalRow(
            response_id=uuid4(),
            subject_id=subject_id,
            prompt_id=prompt_id,
            platform="doubao",
            entity_id=entity_id,
            entity_kind="own",
            brand_id=brand_id,
            mentioned=True,
            mention_count=1,
            mention_rank=1,
            sentiment_score=0.0,
            sentiment_reason="",
            has_domain_link=False,
            cited_on_source=False,
            created_at=datetime(2026, 5, day, tzinfo=timezone.utc),
        )

    current_a = row(2)
    current_b = row(3)
    previous_a = LLMResponseSignalRow(
        response_id=uuid4(),
        subject_id=subject_id,
        prompt_id=prompt_id,
        platform="doubao",
        entity_id="own",
        entity_kind="own",
        brand_id=brand_id,
        mentioned=True,
        mention_count=1,
        mention_rank=1,
        sentiment_score=0.0,
        sentiment_reason="",
        has_domain_link=False,
        cited_on_source=False,
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )
    signals = [current_a, current_b, previous_a]
    windows = build_dual_signal_window(
        signals,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )
    assert len(windows.current.by_entity["own"]) == 2
    assert len(windows.previous.by_entity["own"]) == 1
    assert windows.current.total_voice == 2


def test_window_has_data():
    from datetime import datetime, timezone
    from uuid import uuid4

    from aperix_geo.services.analysis.signal_index import index_signals, window_has_data
    from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow

    assert window_has_data(index_signals([])) is False

    row = LLMResponseSignalRow(
        response_id=uuid4(),
        subject_id=uuid4(),
        prompt_id=uuid4(),
        platform="doubao",
        entity_id="own",
        entity_kind="own",
        brand_id=uuid4(),
        mentioned=True,
        mention_count=1,
        mention_rank=1,
        sentiment_score=0.0,
        sentiment_reason="",
        has_domain_link=False,
        cited_on_source=False,
        created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    assert window_has_data(index_signals([row])) is True


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
                            if "tb_subject_prompts" in sql:
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

    from aperix_geo.services.analysis.entity_sql import (
        query_entity_window,
        window_overview_from_index,
    )
    from aperix_geo.services.analysis.signal_index import index_signals
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    signals = _signals_for_rows(rows, subject, payloads)
    original_window = query_entity_window.override
    original_signals = load_llm_response_signals.override
    query_entity_window.override = lambda db, **kwargs: window_overview_from_index(
        index_signals(signals),
        subject=kwargs["subject"],
    )
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        out = build_topic_visibility_ranks(
            FakeDb(), subject=subject, dt_from=dt_from, dt_to=dt_to
        )
    finally:
        query_entity_window.override = original_window
        load_llm_response_signals.override = original_signals

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
    own_brand_id = uuid.uuid4()
    own_row = LLMResponseSignalRow(
        response_id=response_id,
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        brand_id=own_brand_id,
        mentioned=True,
        mention_count=2,
        mention_rank=1,
        sentiment_score=80.0,
        sentiment_reason=None,
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
        brand_id=uuid.uuid4(),
        mentioned=True,
        mention_count=1,
        mention_rank=2,
        sentiment_score=55.0,
        sentiment_reason=None,
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
    assert metrics.sentiment_label == "positive"


def test_metrics_from_signals_excludes_zero_sentiment():
    subject = _subject_with_competitor()
    created = datetime.now(UTC)
    scored = LLMResponseSignalRow(
        response_id=uuid.uuid4(),
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        brand_id=uuid.uuid4(),
        mentioned=True,
        mention_count=1,
        mention_rank=1,
        sentiment_score=80.0,
        sentiment_reason="good",
        has_domain_link=False,
        cited_on_source=False,
        created_at=created,
    )
    unmentioned = LLMResponseSignalRow(
        response_id=uuid.uuid4(),
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        brand_id=scored.brand_id,
        mentioned=False,
        mention_count=0,
        mention_rank=0,
        sentiment_score=0.0,
        sentiment_reason="",
        has_domain_link=False,
        cited_on_source=False,
        created_at=created,
    )
    metrics = metrics_from_signals([scored, unmentioned], subject=subject)
    assert metrics.sentiment_score == 80.0

    empty = metrics_from_signals([unmentioned], subject=subject)
    assert empty.sentiment_score == 0.0
    assert empty.sentiment_label == "negative"


def test_mentioned_brands_for_response_includes_open_set() -> None:
    subject = _subject_with_competitor()
    entities = list_analysis_entities(subject)
    response_id = uuid.uuid4()
    created = datetime.now(UTC)
    brand_id = uuid.uuid4()
    closed = LLMResponseSignalRow(
        response_id=response_id,
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        brand_id=brand_id,
        mentioned=True,
        mention_count=1,
        mention_rank=1,
        sentiment_score=80.0,
        sentiment_reason="good",
        has_domain_link=False,
        cited_on_source=False,
        created_at=created,
        entity_label="Aperix",
        primary_domain="aperix.com",
    )
    other = LLMResponseSignalRow(
        response_id=response_id,
        subject_id=subject.id,
        prompt_id=closed.prompt_id,
        platform="doubao",
        entity_id="other:stripe",
        entity_kind="other",
        brand_id=uuid.uuid4(),
        mentioned=True,
        mention_count=1,
        mention_rank=2,
        sentiment_score=75.0,
        sentiment_reason="positive",
        has_domain_link=False,
        cited_on_source=False,
        created_at=created,
        entity_label="Stripe",
        primary_domain="stripe.com",
    )

    result = mentioned_brands_for_response(
        response_id,
        all_signals=[closed, other],
        entities=entities,
    )

    assert [row["label"] for row in result] == ["aperix.com", "Stripe"]
    assert result[1]["domain"] == "stripe.com"


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
                brand_id=uuid.uuid4(),
                mentioned=sig.mentioned,
                mention_count=sig.mention_count,
                mention_rank=persist_mention_rank(sig.mention_rank),
                sentiment_score=0.0,
                sentiment_reason="",
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


def test_build_visibility_analysis_flat_payload():
    from datetime import timedelta

    from aperix_geo.services.analysis._series import previous_date_range
    from aperix_geo.services.analysis import build_visibility_analysis
    from aperix_geo.services.analysis.entity_sql import (
        dual_overview_from_signals,
        query_dual_entity_window,
        query_entity_window,
        window_overview_from_index,
    )
    from aperix_geo.services.analysis.signal_index import index_signals
    from aperix_geo.services.analysis.signal_load import load_llm_response_signals

    subject = _subject_with_competitor()
    own_brand_id = uuid.uuid4()
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2, mention_rank=1),
            competitor_signal(mentioned=True, mention_count=1, mention_rank=2),
        ),
        parsed_payload(
            entity_signal(mentioned=False, mention_count=0),
            competitor_signal(mentioned=True, mention_count=3, mention_rank=1),
        ),
    ]
    rows = [_row(payload) for payload in payloads]
    signals = _signals_for_rows(rows, subject, payloads)
    from dataclasses import replace

    signals = [
        replace(row, brand_id=own_brand_id) if row.entity_id == OWN_ENTITY_ID else row
        for row in signals
    ]

    class FakeDb:
        def execute(self, _stmt):
            class R:
                def scalars(self):
                    class S:
                        def all(self):
                            return []

                    return S()

                def scalar_one_or_none(self):
                    return own_brand_id

            return R()

        def flush(self):
            return None

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=7)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    original_overview = query_dual_entity_window.override
    original_window = query_entity_window.override
    original_signals = load_llm_response_signals.override
    query_dual_entity_window.override = lambda db, **kwargs: dual_overview_from_signals(
        signals,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )
    query_entity_window.override = lambda db, **kwargs: window_overview_from_index(
        index_signals(signals),
        subject=subject,
    )
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        out = build_visibility_analysis(
            FakeDb(),
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
        )
    finally:
        query_dual_entity_window.override = original_overview
        query_entity_window.override = original_window
        load_llm_response_signals.override = original_signals

    assert out["entity_id"] == OWN_ENTITY_ID
    assert "own_label" not in out
    assert "focus_label" not in out
    assert "visibility" in out and "rank" in out["visibility"]
    assert out["visibility_chart"]["cur_series"]
    assert out["mention_chart"]["cur_series"]
    assert out["average_rank_chart"]["cur_series"]
    assert len(out["visibility_table"]) == 2
    assert out["topic_visibility_ranks"] == []


def test_citation_sql_share_matches_signal_aggregation():
    from datetime import date

    from aperix_geo.services.analysis.aggregate import (
        citation_share_from_signals,
        daily_citation_share_series_from_signals,
    )
    from aperix_geo.services.analysis.citation_sql import (
        _daily_series_by_label,
        _share_by_label,
    )

    subject = _subject_with_competitor()
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, has_domain_link=True),
            competitor_signal(mentioned=True, has_domain_link=False),
        ),
        parsed_payload(
            entity_signal(mentioned=True, has_domain_link=False),
            competitor_signal(mentioned=True, has_domain_link=True),
        ),
    ]
    rows = [_row(payload) for payload in payloads]
    rows[0].created_at = datetime(2026, 1, 1, tzinfo=UTC)
    rows[1].created_at = datetime(2026, 1, 2, tzinfo=UTC)
    signals = _signals_for_rows(rows, subject, payloads)

    _, signal_share, _ = citation_share_from_signals(signals, subject=subject)
    signal_series = daily_citation_share_series_from_signals(signals, subject=subject)

    by_entity: dict[str, list[int]] = {}
    daily: dict[str, dict[str, list[int]]] = {}
    for row in signals:
        bucket = by_entity.setdefault(row.entity_id, [0, 0])
        day_bucket = daily.setdefault(row.created_at.date().isoformat(), {}).setdefault(
            row.entity_id, [0, 0]
        )
        if row.mentioned:
            bucket[1] += 1
            day_bucket[1] += 1
            if row.has_domain_link:
                bucket[0] += 1
                day_bucket[0] += 1

    class _MetricRow:
        def __init__(self, entity_id: str, with_link: int, mentioned: int, day=None):
            self.entity_id = entity_id
            self.with_link = with_link
            self.mentioned = mentioned
            self.day = day

    metric_rows = [
        _MetricRow(entity_id, counts[0], counts[1])
        for entity_id, counts in by_entity.items()
    ]
    daily_rows = [
        _MetricRow(entity_id, counts[0], counts[1], day=date.fromisoformat(day))
        for day, entities in daily.items()
        for entity_id, counts in entities.items()
    ]

    entities = list_analysis_entities(subject)
    _, sql_share = _share_by_label(metric_rows, entities=entities)
    sql_series = _daily_series_by_label(daily_rows, entities=entities)

    assert sql_share == signal_share
    assert sql_series == signal_series


def test_entity_sql_matches_signal_aggregation():
    from aperix_geo.services.analysis.aggregate import entity_metrics_rows_from_index
    from aperix_geo.services.analysis.entity_sql import (
        _entity_metrics_rows_from_aggs,
        window_overview_from_index,
    )
    from aperix_geo.services.analysis.signal_index import index_signals

    subject = _subject_with_competitor()
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2, mention_rank=1, has_domain_link=True),
            competitor_signal(mentioned=True, mention_count=1, mention_rank=2),
        ),
        parsed_payload(
            entity_signal(mentioned=False, mention_count=0),
            competitor_signal(mentioned=True, mention_count=3, mention_rank=1, has_domain_link=True),
        ),
    ]
    rows = [_row(payload) for payload in payloads]
    signals = _signals_for_rows(rows, subject, payloads)
    entities = list_analysis_entities(subject)
    index = index_signals(signals)
    signal_rows = entity_metrics_rows_from_index(index, subject=subject, entities=entities)

    by_entity: dict[str, dict[str, Any]] = {}
    for row in signals:
        bucket = by_entity.setdefault(
            row.entity_id,
            {
                "response_ids": set(),
                "mentioned_rows": 0,
                "mention_total": 0,
                "mention_with_link": 0,
                "cited_on_source_rows": 0,
                "ranks": [],
                "sentiments": [],
            },
        )
        bucket["response_ids"].add(row.response_id)
        if row.mentioned:
            bucket["mentioned_rows"] += 1
            bucket["mention_total"] += row.mention_count
            if row.has_domain_link:
                bucket["mention_with_link"] += 1
        if row.cited_on_source:
            bucket["cited_on_source_rows"] += 1
        if row.mention_rank > 0:
            bucket["ranks"].append(float(row.mention_rank))
        if row.sentiment_score > 0:
            bucket["sentiments"].append(float(row.sentiment_score))

    class _AggRow:
        pass

    agg_rows = []
    for entity_id, bucket in by_entity.items():
        row = _AggRow()
        row.entity_id = entity_id
        row.response_count = len(bucket["response_ids"])
        row.mentioned_rows = bucket["mentioned_rows"]
        row.mention_total = bucket["mention_total"]
        row.mention_with_link = bucket["mention_with_link"]
        row.cited_on_source_rows = bucket["cited_on_source_rows"]
        ranks = bucket["ranks"]
        row.avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None
        sentiments = bucket["sentiments"]
        row.sentiment_avg = round(sum(sentiments) / len(sentiments), 1) if sentiments else None
        agg_rows.append(row)

    sql_rows = _entity_metrics_rows_from_aggs(
        agg_rows,
        subject=subject,
        entities=entities,
        total_voice=index.total_voice,
    )

    for signal_row, sql_row in zip(
        sorted(signal_rows, key=lambda item: item["id"]),
        sorted(sql_rows, key=lambda item: item["id"]),
    ):
        assert signal_row["metrics"] == sql_row["metrics"]

    overview = window_overview_from_index(index, subject=subject, entities=entities)
    assert overview.total_voice == index.total_voice
    assert len(overview.entity_rows) == len(signal_rows)
