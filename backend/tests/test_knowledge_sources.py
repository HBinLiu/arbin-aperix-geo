"""Tests for knowledge source management."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from aperix_geo.db.models import SubjectType
from aperix_geo.services.knowledge.sources import delete_knowledge_source, upsert_user_input_text


def _subject() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="示例品牌",
        website_url="https://example.com",
        aliases=["别名"],
    )


def test_upsert_user_input_text_creates_knowledge_and_source() -> None:
    subject = _subject()
    db = MagicMock()
    db.scalar.side_effect = [None, None]

    with (
        patch("aperix_geo.services.knowledge.sources.schedule_knowledge_reindex"),
        patch(
            "aperix_geo.services.knowledge.sources.get_subject_knowledge_detail",
            return_value={"knowledge": {"status": "verified"}, "sources": [], "chunk_count": 0},
        ),
    ):
        result = upsert_user_input_text(
            db,
            subject=subject,
            user_id=uuid4(),
            text="品牌介绍正文",
        )

    assert db.add.call_count == 2
    assert result["knowledge"]["status"] == "verified"


def test_upsert_user_input_text_schedules_reindex() -> None:
    subject = _subject()
    knowledge = SimpleNamespace(
        tenant_id=subject.tenant_id,
        subject_id=subject.id,
        status="verified",
        index_status="indexed",
        narrative_json={},
    )
    source = SimpleNamespace(
        kind="user_input",
        title="品牌介绍",
        raw_text="旧内容",
        char_count=3,
        parse_status="ok",
        parse_error="",
    )

    db = MagicMock()
    db.scalar.side_effect = [knowledge, source]
    user_id = uuid4()

    with (
        patch("aperix_geo.services.knowledge.sources.schedule_knowledge_reindex") as schedule,
        patch(
            "aperix_geo.services.knowledge.sources.get_subject_knowledge_detail",
            return_value={"knowledge": {"status": "verified"}, "sources": [], "chunk_count": 0},
        ),
    ):
        upsert_user_input_text(
            db,
            subject=subject,
            user_id=user_id,
            text="更新后的介绍",
        )

    schedule.assert_called_once_with(db, subject=subject, knowledge=knowledge, user_id=user_id)
    assert source.raw_text == "更新后的介绍"
    assert knowledge.narrative_json["overview"] == "更新后的介绍"


def test_upsert_user_input_text_rejects_empty() -> None:
    subject = _subject()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        upsert_user_input_text(db, subject=subject, user_id=uuid4(), text="   ")

    assert exc.value.status_code == 400


def test_delete_knowledge_source_rejects_homepage() -> None:
    subject = _subject()
    knowledge = SimpleNamespace(
        status="verified",
        index_status="indexed",
        narrative_json={},
    )
    source = SimpleNamespace(
        kind="homepage",
        storage_key="",
    )

    db = MagicMock()
    db.scalar.side_effect = [knowledge, source]

    with pytest.raises(HTTPException) as exc:
        delete_knowledge_source(db, subject=subject, user_id=uuid4(), source_id=uuid4())

    assert exc.value.status_code == 400
