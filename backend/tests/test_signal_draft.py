"""Tests for flat entity signal drafts during sampling parse."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.signals import build_llm_response_signal_rows
from aperix_geo.services.sampling.signal_draft import drafts_from_records, drafts_to_records
from tests.parsed_fixtures import competitor_signal, entity_signal, parsed_payload


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_parse_attaches_entity_signals() -> None:
    subject = _subject()
    parsed = parse_llm_output("Aperix 优于 Beta。", subject=subject)
    assert len(parsed.entity_signals) == 2
    own = next(d for d in parsed.entity_signals if d.entity_id == OWN_ENTITY_ID)
    comp = next(d for d in parsed.entity_signals if d.entity_kind == "competitor")
    assert own.mentioned is True
    assert comp.mentioned is True
    assert own.mention_rank == 1


def test_entity_signals_excluded_from_storage_dict() -> None:
    subject = _subject()
    parsed = parse_llm_output("推荐 Aperix。", subject=subject)
    stored = parsed.to_dict()
    assert "entity_signals" not in stored
    restored = ParsedSamplingResult.from_dict(stored)
    assert restored.entity_signals == []


def test_draft_records_match_attached_signals() -> None:
    subject = _subject()
    parsed = parse_llm_output("Beta 在前，Aperix 在后。", subject=subject)
    rebuilt = drafts_from_records(drafts_to_records(parsed.entity_signals))
    assert len(rebuilt) == len(parsed.entity_signals)
    for original, copy in zip(parsed.entity_signals, rebuilt, strict=True):
        assert original.entity_id == copy.entity_id
        assert original.mentioned == copy.mentioned
        assert original.mention_rank == copy.mention_rank


def test_parsed_sampling_result_round_trip_from_fixtures() -> None:
    original = ParsedSamplingResult.from_dict(
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2, sentiment_score=90.0, sentiment_label="positive"),
            competitor_signal(mentioned=True, mention_count=1),
        )
    )
    restored = ParsedSamplingResult.from_dict(original.to_dict())
    assert len(original.entity_signals) == 2
    assert restored.entity_signals == []
    own = next(sig for sig in original.entity_signals if sig.entity_id == "own")
    assert own.mentioned is True
    assert own.mention_count == 2
    assert own.sentiment_score == 90.0


def test_build_rows_from_parsed_entity_signals() -> None:
    from datetime import UTC, datetime

    subject = _subject()
    parsed = parse_llm_output("推荐 Aperix。", subject=subject)
    rows = build_llm_response_signal_rows(
        response_id=uuid.uuid4(),
        subject_id=subject.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        created_at=datetime.now(UTC),
        entity_signals=parsed.entity_signals,
    )
    assert len(rows) == 2
