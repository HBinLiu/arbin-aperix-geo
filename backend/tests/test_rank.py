"""Tests for dashboard rank board API payload."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.rank import build_rank
from aperix_geo.services.analysis.entity_sql import (
    query_entity_window,
    window_overview_from_index,
)
from aperix_geo.services.analysis.entity import list_analysis_entities
from aperix_geo.services.analysis.signal_index import index_signals
from tests.parsed_fixtures import competitor_signal, entity_signal, parsed_payload, signal_rows_from_payload


def _subject_with_competitor() -> Subject:
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    return Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
        competitors=[
            Competitor(
                id=competitor_id,
                subject_id=subject_id,
                brand="Beta",
                domain="beta.com",
            )
        ],
    )


def test_build_rank_returns_sorted_items_with_display_names() -> None:
    subject = _subject_with_competitor()
    comp_id = str(subject.competitors[0].id)
    payloads = [
        parsed_payload(
            entity_signal(mentioned=True, mention_count=2, mention_rank=1),
            competitor_signal(entity_id=comp_id, mentioned=True, mention_count=1, mention_rank=2),
        ),
    ]
    rows = [
        type("Row", (), {
            "id": uuid.uuid4(),
            "prompt_id": uuid.uuid4(),
            "platform": "doubao",
            "created_at": datetime(2026, 6, 10, tzinfo=UTC),
            "parsed": payloads[0],
        })(),
    ]
    signals = signal_rows_from_payload(rows, subject, parsed_payloads=payloads)
    original = query_entity_window.override
    query_entity_window.override = lambda db, **kwargs: window_overview_from_index(
        index_signals(signals),
        subject=subject,
        entities=list_analysis_entities(subject),
    )
    try:
        payload = build_rank(
            db=None,  # type: ignore[arg-type]
            subject=subject,
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
        )
    finally:
        query_entity_window.override = original

    assert payload["own_label"] == "aperix.com"
    assert len(payload["items"]) == 2
    own = next(item for item in payload["items"] if item["is_own"])
    comp = next(item for item in payload["items"] if not item["is_own"])
    assert own["display_name"] == "Aperix"
    assert own["domain"] == "aperix.com"
    assert comp["display_name"] == "Beta"
    assert comp["domain"] == "beta.com"
    assert payload["items"][0]["visibility_rate"] >= payload["items"][1]["visibility_rate"]
