"""Tests for subject catalog Redis cache (entities, topics)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.analysis.metrics import build_analysis_entities
from aperix_geo.services.catalog import cache as catalog_cache
from aperix_geo.services.catalog.entities import get_analysis_entities


def _subject() -> Subject:
    subject = Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )
    subject.competitors = []
    return subject


def test_get_analysis_entities_uses_cache_on_second_call() -> None:
    subject = _subject()
    catalog_cache._ENTITIES_CACHE.clear()

    with patch.object(catalog_cache, "_catalog_cache_ttl_s", return_value=3600):
        first = get_analysis_entities(subject)
        second = get_analysis_entities(subject)

    assert first == second
    assert first == build_analysis_entities(subject)


def test_clear_analysis_entities_cache_forces_rebuild() -> None:
    subject = _subject()
    catalog_cache._ENTITIES_CACHE.clear()

    with patch.object(catalog_cache, "_catalog_cache_ttl_s", return_value=3600):
        get_analysis_entities(subject)
        catalog_cache.clear_analysis_entities_cache(subject.id)

        with patch(
            "aperix_geo.services.catalog.entities.build_analysis_entities",
            wraps=build_analysis_entities,
        ) as mock_build:
            get_analysis_entities(subject)
            assert mock_build.call_count == 1


def test_list_subject_topics_uses_cache() -> None:
    from aperix_geo.services.catalog.topics import list_subject_topics

    subject_id = uuid4()
    topic_id = uuid4()
    created_at = datetime(2026, 6, 1, tzinfo=UTC)
    row = SimpleNamespace(
        id=topic_id,
        subject_id=subject_id,
        name="支付",
        created_at=created_at,
    )
    catalog_cache._TOPICS_CACHE.clear()

    mock_db = MagicMock()
    mock_db.execute.return_value.scalars.return_value.all.return_value = [row]

    with patch.object(catalog_cache, "_catalog_cache_ttl_s", return_value=3600):
        first = list_subject_topics(mock_db, subject_id=subject_id)
        second = list_subject_topics(mock_db, subject_id=subject_id)

    assert mock_db.execute.call_count == 1
    assert len(first) == 1
    assert first[0].name == "支付"
    assert second[0].id == topic_id
