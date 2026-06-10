"""Tests for prompt detail response listings."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from aperix_geo.services.analysis import _query
from aperix_geo.services.analysis import prompt_detail as mod


def test_build_prompt_detail_responses_groups_chat_and_citation() -> None:
    subject = SimpleNamespace(
        id=uuid4(),
        monitoring_scope={"region": "US"},
    )
    prompt_id = uuid4()
    rows = [
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="chatgpt",
            raw_text="Reply with brand mention",
            created_at=datetime(2026, 6, 9, 4, 3, 42, tzinfo=UTC),
            parsed={
                "mentions_own": True,
                "rank_own": 14,
                "citation_urls_own": ["https://example.com/page"],
                "cited_own_domain": True,
            },
        ),
        SimpleNamespace(
            id=uuid4(),
            prompt_id=prompt_id,
            platform="gemini",
            raw_text="No mention",
            created_at=datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC),
            parsed={"mentions_own": False},
        ),
    ]

    original = _query.responses_in_window.override
    _query.responses_in_window.override = lambda *args, **kwargs: rows
    try:
        result = mod.build_prompt_detail_responses(
            db=None,  # type: ignore[arg-type]
            subject=subject,  # type: ignore[arg-type]
            dt_from=datetime(2026, 6, 1, tzinfo=UTC),
            dt_to=datetime(2026, 6, 30, tzinfo=UTC),
            prompt_id=prompt_id,
        )
    finally:
        _query.responses_in_window.override = original

    assert result["region"] == "US"
    assert len(result["chat_responses"]) == 2
    assert len(result["citation_responses"]) == 1
    assert result["chat_responses"][0]["mentioned"] is True
    assert result["chat_responses"][0]["rank"] == 14.0
    assert result["chat_responses"][0]["region"] == "US"
    assert result["citation_responses"][0]["cited_own_domain"] is True
