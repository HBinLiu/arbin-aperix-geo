"""Tests for knowledge indexing service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.db.models import EPOCH, KnowledgeSource, SubjectKnowledge, ZERO_UUID
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError, KnowledgeNotReadyError
from aperix_geo.services.knowledge.index import _index_verified_knowledge, index_subject_knowledge


def _settings() -> Settings:
    return Settings(
        embedding_api_key="test-key",
        embedding_dimensions=1024,
        embedding_batch_size=25,
        knowledge_chunk_size=500,
        knowledge_chunk_overlap=64,
    )


def _knowledge(*, status: str = "verified", version: int = 1) -> SubjectKnowledge:
    return SubjectKnowledge(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        status=status,
        version=version,
        index_status="pending",
        indexed_version=0,
        index_error="",
        identity_json={},
        facts_json={},
        relations_json={},
        narrative_json={},
        voice_json={},
        verified_at=EPOCH,
        verified_by_user_id=ZERO_UUID,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _source(*, subject_id: uuid.UUID, tenant_id: uuid.UUID, text: str) -> KnowledgeSource:
    return KnowledgeSource(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=subject_id,
        kind="user_input",
        title="品牌介绍",
        raw_text=text,
        char_count=len(text),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def test_index_subject_knowledge_requires_verified() -> None:
    db = MagicMock()
    knowledge = _knowledge(status="draft")
    db.scalar.return_value = knowledge

    with pytest.raises(KnowledgeNotReadyError):
        index_subject_knowledge(db, knowledge.subject_id, settings=_settings())


@patch("aperix_geo.services.knowledge.index.embed_texts")
def test_index_verified_knowledge_inserts_chunks(mock_embed: MagicMock) -> None:
    knowledge = _knowledge()
    text = "品牌介绍正文。" * 80
    source = _source(subject_id=knowledge.subject_id, tenant_id=knowledge.tenant_id, text=text)
    mock_embed.return_value = ([[0.0] * 1024 for _ in range(2)], {"total_tokens": 10})

    db = MagicMock()
    db.scalars.side_effect = [
        iter([source]),
        iter([]),
    ]

    result = _index_verified_knowledge(db, knowledge, settings=_settings())

    assert result.chunks_created == 2
    assert result.chunks_skipped == 0
    assert result.sources_indexed == 1
    assert mock_embed.called
    assert db.add.call_count == 2


@patch("aperix_geo.services.knowledge.index.embed_texts")
def test_index_skips_duplicate_content_hash(mock_embed: MagicMock) -> None:
    knowledge = _knowledge()
    text = "重复内容" * 200
    source = _source(subject_id=knowledge.subject_id, tenant_id=knowledge.tenant_id, text=text)
    from aperix_geo.services.knowledge.chunk import chunk_text
    from aperix_geo.services.knowledge.index import _content_hash

    first = chunk_text(text, chunk_size=500, overlap=64)[0]
    existing = _content_hash(first.text)

    mock_embed.return_value = ([[0.1] * 1024], {"total_tokens": 1})
    db = MagicMock()
    db.scalars.side_effect = [
        iter([source]),
        iter([existing]),
    ]

    result = _index_verified_knowledge(db, knowledge, settings=_settings())
    assert result.chunks_skipped >= 1


@patch("aperix_geo.services.knowledge.index.embed_texts")
def test_index_subject_knowledge_marks_failed_on_embed_error(mock_embed: MagicMock) -> None:
    knowledge = _knowledge()
    source = _source(
        subject_id=knowledge.subject_id,
        tenant_id=knowledge.tenant_id,
        text="失败测试" * 120,
    )
    mock_embed.side_effect = KnowledgeIndexError("boom")

    db = MagicMock()
    db.scalar.return_value = knowledge
    db.scalars.side_effect = [
        iter([source]),
        iter([]),
    ]

    with pytest.raises(KnowledgeIndexError):
        index_subject_knowledge(db, knowledge.subject_id, settings=_settings())

    assert knowledge.index_status == "failed"
    assert "boom" in knowledge.index_error
