"""Tests for knowledge read service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from aperix_geo.services.knowledge.read import get_subject_knowledge_detail


def test_get_subject_knowledge_detail_empty() -> None:
    db = MagicMock()
    db.scalar.return_value = None
    db.scalars.return_value.all.return_value = []

    subject_id = uuid4()
    result = get_subject_knowledge_detail(db, subject_id)

    assert result["knowledge"] is None
    assert result["sources"] == []
    assert result["chunk_count"] == 0


def test_get_subject_knowledge_detail_with_payload() -> None:
    subject_id = uuid4()
    knowledge = SimpleNamespace(
        id=uuid4(),
        subject_id=subject_id,
        status="verified",
        version=2,
        index_status="indexed",
        indexed_version=2,
        index_error="",
        identity_json={
            "primary_name": "示例品牌",
            "aliases": ["别名"],
            "negative_aliases": [],
            "category": "SaaS",
            "disambiguation": "",
            "official_url": "https://example.com",
        },
        facts_json={
            "industry": "营销科技",
            "icp": "中小企业",
            "products": ["产品A"],
            "pain_points": [],
            "differentiators": ["差异化"],
        },
        relations_json={},
        narrative_json={"overview": "品牌概述", "capabilities": ["能力1"]},
        voice_json={"tone": "专业", "forbidden_words": ["最便宜"]},
        verified_at=datetime(2026, 7, 1, tzinfo=UTC),
        updated_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    source = SimpleNamespace(
        id=uuid4(),
        kind="user_input",
        title="品牌介绍",
        uri="",
        mime_type="",
        file_size=0,
        char_count=320,
        parse_status="ok",
        parse_error="",
        sort_order=0,
        raw_text="品牌介绍正文",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    db = MagicMock()
    db.scalar.side_effect = [knowledge, 3]
    db.scalars.return_value.all.return_value = [source]

    result = get_subject_knowledge_detail(db, subject_id)

    assert result["knowledge"] is not None
    assert result["knowledge"]["status"] == "verified"
    assert result["knowledge"]["version"] == 2
    assert result["chunk_count"] == 3
    assert len(result["sources"]) == 1
    assert result["sources"][0]["kind"] == "user_input"
    assert "identity" not in result["knowledge"]
    assert "facts" not in result["knowledge"]
