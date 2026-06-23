"""Tests for analysis responses endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.analysis import responses as mod
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.analysis.responses_sql import query_prompt_chat_page
from aperix_geo.services.analysis.signal_load import load_llm_response_other_brand_signals, load_llm_response_signals
from tests.parsed_fixtures import entity_signal, parsed_payload, signal_rows_from_payload
from tests.responses_mem import mem_prompt_chat_page


def _subject() -> Subject:
    return Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


def _patch_prompt_chat(signals, other_signals=None):
    original_chat = query_prompt_chat_page.override
    original_signals = load_llm_response_signals.override
    original_other = load_llm_response_other_brand_signals.override
    query_prompt_chat_page.override = mem_prompt_chat_page
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    load_llm_response_other_brand_signals.override = lambda *args, **kwargs: other_signals or []
    return original_chat, original_signals, original_other


def _restore_prompt_chat(original_chat, original_signals, original_other):
    query_prompt_chat_page.override = original_chat
    load_llm_response_signals.override = original_signals
    load_llm_response_other_brand_signals.override = original_other


def test_build_analysis_responses_prompt_chat_mode() -> None:
    subject = _subject()
    prompt_id = uuid4()
    payloads = [
        parsed_payload(entity_signal(mentioned=True, mention_rank=14, sentiment_score=80.0)),
        parsed_payload(entity_signal(mentioned=False, sentiment_score=0.0)),
    ]
    rows = [
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="chatgpt",
            raw_text="Reply with brand mention",
            created_at=datetime(2026, 6, 9, 4, 3, 42, tzinfo=UTC),
            parsed=payloads[0],
        ),
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="gemini",
            raw_text="No mention",
            created_at=datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC),
            parsed=payloads[1],
        ),
    ]
    prompt = SimpleNamespace(id=prompt_id, text="Best CRM tools?")
    signals = signal_rows_from_payload(rows, subject, parsed_payloads=payloads)

    from aperix_geo.services.analysis import _query

    original_responses = _query.responses_in_window.override
    _query.responses_in_window.override = lambda *args, **kwargs: rows
    originals = _patch_prompt_chat(signals)
    db = SimpleNamespace(get=lambda model, pk: prompt if pk == prompt_id else None)
    try:
        result = mod.build_analysis_responses(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
            entity_id=OWN_ENTITY_ID,
            sentiment_label=None,
        )
    finally:
        _query.responses_in_window.override = original_responses
        _restore_prompt_chat(*originals)

    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["items"][0]["mentioned"] is True
    assert result["items"][0]["rank"] == 14.0
    assert result["items"][0]["platform_id"] == "chatgpt"
    assert result["items"][1]["mentioned"] is False


def test_build_analysis_responses_pagination() -> None:
    subject = _subject()
    prompt_id = uuid4()
    payloads = [
        parsed_payload(entity_signal(mentioned=True, mention_rank=1, sentiment_score=90.0)),
        parsed_payload(entity_signal(mentioned=True, mention_rank=2, sentiment_score=70.0)),
        parsed_payload(entity_signal(mentioned=True, mention_rank=3, sentiment_score=50.0)),
    ]
    rows = [
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="chatgpt",
            raw_text=f"Reply {index}",
            created_at=datetime(2026, 6, 10 - index, tzinfo=UTC),
            parsed=payloads[index],
        )
        for index in range(3)
    ]
    prompt = SimpleNamespace(id=prompt_id, text="Best CRM tools?")
    signals = signal_rows_from_payload(rows, subject, parsed_payloads=payloads)

    from aperix_geo.services.analysis import _query

    original_responses = _query.responses_in_window.override
    _query.responses_in_window.override = lambda *args, **kwargs: rows
    originals = _patch_prompt_chat(signals)
    db = SimpleNamespace(get=lambda model, pk: prompt if pk == prompt_id else None)
    try:
        page_one = mod.build_analysis_responses(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
            entity_id=OWN_ENTITY_ID,
            sentiment_label=None,
            page=1,
            page_size=2,
        )
        page_two = mod.build_analysis_responses(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
            entity_id=OWN_ENTITY_ID,
            sentiment_label=None,
            page=2,
            page_size=2,
        )
        sorted_by_score = mod.build_analysis_responses(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
            entity_id=OWN_ENTITY_ID,
            sentiment_label=None,
            sort_by="sentiment_score",
            order="desc",
        )
    finally:
        _query.responses_in_window.override = original_responses
        _restore_prompt_chat(*originals)

    assert page_one["total"] == 3
    assert len(page_one["items"]) == 2
    assert len(page_two["items"]) == 1
    assert sorted_by_score["items"][0]["sentiment_score"] == 90.0


def test_build_analysis_responses_rank_sort() -> None:
    subject = _subject()
    prompt_id = uuid4()
    payloads = [
        parsed_payload(entity_signal(mentioned=True, mention_rank=5, sentiment_score=50.0)),
        parsed_payload(entity_signal(mentioned=True, mention_rank=1, sentiment_score=80.0)),
        parsed_payload(entity_signal(mentioned=False, sentiment_score=0.0)),
    ]
    rows = [
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="chatgpt",
            raw_text=f"Reply {index}",
            created_at=datetime(2026, 6, 10 - index, tzinfo=UTC),
            parsed=payloads[index],
        )
        for index in range(3)
    ]
    prompt = SimpleNamespace(id=prompt_id, text="Best CRM tools?")
    signals = signal_rows_from_payload(rows, subject, parsed_payloads=payloads)

    from aperix_geo.services.analysis import _query

    original_responses = _query.responses_in_window.override
    _query.responses_in_window.override = lambda *args, **kwargs: rows
    originals = _patch_prompt_chat(signals)
    db = SimpleNamespace(get=lambda model, pk: prompt if pk == prompt_id else None)
    try:
        asc = mod.build_analysis_responses(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
            entity_id=OWN_ENTITY_ID,
            sentiment_label=None,
            sort_by="rank",
            order="asc",
        )
    finally:
        _query.responses_in_window.override = original_responses
        _restore_prompt_chat(*originals)

    assert [row["rank"] for row in asc["items"]] == [1.0, 5.0, None]
