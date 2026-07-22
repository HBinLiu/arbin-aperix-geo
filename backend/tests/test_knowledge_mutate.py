"""Tests for knowledge mutate service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from aperix_geo.db.models import SubjectType
from aperix_geo.services.knowledge.mutate import schedule_knowledge_reindex


def _knowledge_row(*, version: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        subject_id=uuid4(),
        version=version,
        status="draft",
        index_status="pending",
        index_error="",
        identity_json={"primary_name": "示例品牌", "aliases": [], "official_url": ""},
        relations_json={},
        verified_at=datetime(2026, 7, 1, tzinfo=UTC),
        verified_by_user_id=uuid4(),
    )


def _subject(subject_id) -> SimpleNamespace:
    return SimpleNamespace(
        id=subject_id,
        type=SubjectType.brand,
        brand="示例品牌",
        domain="example.com",
        website_url="https://example.com",
        aliases=[],
    )


def test_schedule_knowledge_reindex_bumps_version() -> None:
    subject_id = uuid4()
    user_id = uuid4()
    subject = _subject(subject_id)
    knowledge = _knowledge_row(version=1)

    db = MagicMock()

    schedule_knowledge_reindex(db, subject=subject, knowledge=knowledge, user_id=user_id)

    assert knowledge.version == 2
    assert knowledge.status == "verified"
    assert knowledge.verified_by_user_id == user_id
    assert knowledge.index_status == "pending"
    assert knowledge.relations_json["extract_status"] == "pending"
    db.flush.assert_called()
