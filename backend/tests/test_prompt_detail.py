"""Tests for prompt detail response listings."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.analysis import _query
from aperix_geo.services.analysis import prompt_detail as mod
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.signals import build_llm_response_signal_rows
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from tests.parsed_fixtures import entity_signal, parsed_payload, signal_rows_from_payload


def _subject() -> Subject:
    return Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


def _signals_from_rows(rows, subject: Subject, payloads: list[dict]) -> list[LLMResponseSignalRow]:
    return signal_rows_from_payload(rows, subject, parsed_payloads=payloads)


def test_build_prompt_detail_responses_groups_chat_and_citation() -> None:
    subject = _subject()
    prompt_id = uuid4()
    payloads = [
        parsed_payload(
            entity_signal(
                mentioned=True,
                mention_rank=14,
                has_domain_link=True,
                cited_on_source=True,
            ),
            citation_urls_own=["https://example.com/page"],
        ),
        parsed_payload(entity_signal(mentioned=False)),
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

    signals = _signals_from_rows(rows, subject, payloads)
    original_responses = _query.responses_in_window.override
    original_signals = load_llm_response_signals.override
    _query.responses_in_window.override = lambda *args, **kwargs: rows
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    try:
        result = mod.build_prompt_detail_responses(
            db=None,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
        )
    finally:
        _query.responses_in_window.override = original_responses
        load_llm_response_signals.override = original_signals

    assert result["entity_id"] == OWN_ENTITY_ID
    assert len(result["chat_responses"]) == 2
    assert len(result["citation_responses"]) == 1
    assert result["chat_responses"][0]["mentioned"] is True
    assert result["chat_responses"][0]["rank"] == 14.0
    assert result["citation_responses"][0]["cited_on_source"] is True
