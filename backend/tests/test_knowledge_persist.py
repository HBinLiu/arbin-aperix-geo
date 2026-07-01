"""Tests for brand knowledge persist at finalize."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.knowledge.persist import persist_brand_knowledge_from_setup


def test_persist_brand_knowledge_writes_sources() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        domain="",
        brand="深睿医疗",
        website_url="https://example.com",
        aliases=["DeepWise"],
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    session = {
        "materials_saved": True,
        "brand": "深睿医疗",
        "brand_intro": "品牌介绍" * 80,
        "website_url": "https://example.com",
        "profile": {"industry": "医疗 AI", "customers": "医院", "features": "影像诊断"},
        "upload_files": [
            {
                "id": "f1",
                "name": "产品.txt",
                "mime": "text/plain",
                "size": 10,
                "storage_key": "",
                "extracted_text": "产品说明",
            }
        ],
        "research_payload": {
            "homepage": {"url": "https://example.com", "text": "首页正文"},
        },
    }
    db = MagicMock()
    db.flush = MagicMock()

    knowledge = persist_brand_knowledge_from_setup(
        db,
        subject=subject,
        setup_session=session,
        user_id=uuid.uuid4(),
    )

    assert knowledge is not None
    assert knowledge.status == "verified"
    assert knowledge.version == 1
    assert knowledge.identity_json["official_url"] == "https://example.com"
    assert db.add.call_count >= 3
