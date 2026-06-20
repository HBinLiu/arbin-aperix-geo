"""Tests for LLM response signal persistence."""

from unittest.mock import MagicMock
from uuid import uuid4

from aperix_geo.db.models import LLMResponse, Subject, SubjectType
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.signals.persist import replace_llm_response_signals_for_response


def test_replace_llm_response_signals_flushes_delete_before_insert() -> None:
    db = MagicMock()
    row = LLMResponse(
        id=uuid4(),
        prompt_id=uuid4(),
        platform="doubao",
        created_at=None,
    )
    subject = Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )
    parsed = ParsedSamplingResult(entity_signals=[])

    replace_llm_response_signals_for_response(
        db,
        row=row,
        subject=subject,
        parsed=parsed,
        brands_by_entity_id={},
    )

    db.flush.assert_called_once()
    assert db.execute.call_count == 1
    db.add_all.assert_called_once()
