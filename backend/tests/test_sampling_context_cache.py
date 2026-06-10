"""Tests for sampling subject/prompt context cache."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.cache.context import (
    _deserialize_subject,
    _serialize_subject,
    clear_sampling_context_cache,
    load_prompt_text_cached,
    load_subject_with_competitors_cached,
)


def _subject(*, brand: str = "Aperix") -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand=brand,
        aliases=["艾佩克斯"],
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
            aliases=["贝塔"],
        ),
    ]
    return subject


def test_subject_roundtrip_serialization() -> None:
    subject = _subject()
    restored = _deserialize_subject(_serialize_subject(subject))
    assert restored.brand == "Aperix"
    assert restored.aliases == ["艾佩克斯"]
    assert len(restored.competitors) == 1
    assert restored.competitors[0].brand == "Beta"
    assert restored.competitors[0].aliases == ["贝塔"]


@patch("aperix_geo.services.sampling.cache.context.load_subject_with_competitors")
def test_load_subject_cached_hits_l1_without_db(mock_load: MagicMock) -> None:
    clear_sampling_context_cache()
    subject = _subject()
    db = MagicMock()
    mock_load.return_value = subject

    first = load_subject_with_competitors_cached(db, subject.id)
    assert first is subject
    mock_load.assert_called_once()

    second = load_subject_with_competitors_cached(db, subject.id)
    assert second is not None
    assert second.id == subject.id
    assert second.brand == subject.brand
    mock_load.assert_called_once()


@patch("aperix_geo.utils.cache.tiered_json.redis_set_json_exat")
@patch("aperix_geo.utils.cache.tiered_json.redis_get_json", return_value=None)
def test_load_prompt_text_cached(_mock_redis_get: MagicMock, _mock_redis_set: MagicMock) -> None:
    clear_sampling_context_cache()
    prompt_id = uuid.uuid4()
    db = MagicMock()
    prompt = MagicMock()
    prompt.text = "推荐 Aperix 吗？"
    db.get.return_value = prompt

    assert load_prompt_text_cached(db, prompt_id) == "推荐 Aperix 吗？"
    db.get.assert_called_once()

    assert load_prompt_text_cached(db, prompt_id) == "推荐 Aperix 吗？"
    db.get.assert_called_once()
