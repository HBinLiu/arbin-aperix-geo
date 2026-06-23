"""Tests for prompt detail page payload."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.analysis import _query
from aperix_geo.services.analysis import prompt_detail as mod
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, list_analysis_entities
from aperix_geo.services.analysis.entity_sql import (
    dual_overview_from_signals,
    query_dual_entity_window,
)
from aperix_geo.services.analysis.grouped_sql import query_platform_metrics
from aperix_geo.services.analysis.signal_load import (
    LLMResponseSignalRow,
    load_llm_response_other_brand_signals,
    load_llm_response_signals,
)
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


def test_build_prompt_detail_groups_chat_and_citation() -> None:
    subject = _subject()
    prompt_id = uuid4()
    topic_id = uuid4()
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
    prompt = SimpleNamespace(
        id=prompt_id,
        subject_id=subject.id,
        topic_id=topic_id,
        text="Best CRM tools?",
        search_intent="informational",
    )
    topic = SimpleNamespace(id=topic_id, name="CRM")

    signals = _signals_from_rows(rows, subject, payloads)
    dt_from = datetime(2026, 6, 1, tzinfo=UTC)
    dt_to = datetime(2026, 6, 30, tzinfo=UTC)
    entities = list_analysis_entities(subject)

    original_responses = _query.responses_in_window.override
    original_signals = load_llm_response_signals.override
    original_other_signals = load_llm_response_other_brand_signals.override
    original_dual = query_dual_entity_window.override
    original_platform = query_platform_metrics.override

    _query.responses_in_window.override = lambda *args, **kwargs: rows
    load_llm_response_signals.override = lambda *args, **kwargs: signals
    load_llm_response_other_brand_signals.override = lambda *args, **kwargs: []

    def _dual_overview(db, **kwargs):
        return dual_overview_from_signals(
            signals,
            subject=subject,
            dt_from=kwargs["dt_from"],
            dt_to=kwargs["dt_to"],
            prev_from=kwargs["prev_from"],
            prev_to=kwargs["prev_to"],
            entities=entities,
        )

    query_dual_entity_window.override = _dual_overview
    query_platform_metrics.override = lambda db, **kwargs: [
        {
            "platform": "chatgpt",
            "visibility_rate": 1.0,
            "average_rank": 14.0,
            "citation_rate": 1.0,
        },
        {
            "platform": "gemini",
            "visibility_rate": 0.0,
            "average_rank": None,
            "citation_rate": 0.0,
        },
    ]

    db = SimpleNamespace(
        get=lambda model, pk: prompt if pk == prompt_id else topic if pk == topic_id else None
    )
    try:
        result = mod.build_prompt_detail(
            db=db,  # type: ignore[arg-type]
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            prompt_id=prompt_id,
        )
    finally:
        _query.responses_in_window.override = original_responses
        load_llm_response_signals.override = original_signals
        load_llm_response_other_brand_signals.override = original_other_signals
        query_dual_entity_window.override = original_dual
        query_platform_metrics.override = original_platform

    assert result["entity_id"] == OWN_ENTITY_ID
    assert result["prompt_text"] == "Best CRM tools?"
    assert result["topic_name"] == "CRM"
    assert result["visibility_rate"] == 0.5
    assert result["average_rank"] == 14.0
    assert result["citation_rate"] == 1.0
    assert len(result["visibility_series"]) == 2
    assert len(result["platforms"]) == 2
    assert result["opportunity"] is not None
    assert result["opportunity"]["mention_priority"] == "medium"
    assert "chat_responses" not in result
    assert len(result["citation_responses"]) == 1
    assert result["citation_responses"][0]["cited_on_source"] is True
