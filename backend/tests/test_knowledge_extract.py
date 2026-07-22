"""Tests for knowledge graph schema / facts projection / extract."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import EPOCH, KnowledgeSource, SubjectKnowledge, ZERO_UUID
from aperix_geo.services.knowledge.exceptions import KnowledgeExtractError, KnowledgeNotReadyError
from aperix_geo.services.knowledge.graph.extract import extract_subject_knowledge
from aperix_geo.services.knowledge.graph.schema import (
    ExtractStatus,
    NodeType,
    normalize_llm_graph,
    parse_relations_json,
    stable_node_id,
)
from aperix_geo.services.knowledge.graph.sync_facts import sync_facts_from_graph


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
        identity_json={"primary_name": "Aperix", "aliases": ["阿佩"]},
        facts_json={"industry": "营销科技", "icp": "", "products": [], "pain_points": []},
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
        parse_status="ok",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def test_normalize_llm_graph_ensures_brand_and_stable_ids() -> None:
    source_id = str(uuid.uuid4())
    graph = normalize_llm_graph(
        {
            "nodes": [
                {"type": "product", "label": "可见度监测", "source_ids": [source_id], "confidence": 0.9},
                {"type": "pain", "label": "AI 搜不到品牌", "source_ids": [source_id], "confidence": 0.8},
                {"type": "unknown", "label": "应丢弃", "confidence": 1.0},
            ],
            "edges": [
                {
                    "type": "solves",
                    "from": "可见度监测",
                    "to": "AI 搜不到品牌",
                    "source_ids": [source_id],
                    "evidence": "帮助品牌在 AI 搜索中被看见",
                    "confidence": 0.88,
                },
                {"type": "solves", "from": "可见度监测", "to": "不存在", "confidence": 0.9},
            ],
        },
        allowed_source_ids={source_id},
        brand_label="Aperix",
        brand_aliases=["阿佩"],
        default_source_ids=[source_id],
        extracted_at=datetime(2026, 7, 21, tzinfo=UTC),
    )

    assert graph.extract_status == ExtractStatus.ready
    assert any(n.type == NodeType.brand and n.label == "Aperix" for n in graph.nodes)
    assert stable_node_id("product", "可见度监测") in {n.id for n in graph.nodes}
    assert len(graph.edges) == 1
    assert graph.edges[0].type.value == "solves"
    storage = graph.to_storage()
    assert storage["nodes"]
    api = graph.to_api()
    assert api is not None
    assert api["extract_status"] == "ready"


def test_sync_facts_from_graph() -> None:
    source_id = str(uuid.uuid4())
    graph = normalize_llm_graph(
        {
            "nodes": [
                {"type": "product", "label": "产品A", "confidence": 0.9},
                {"type": "pain", "label": "获客难", "confidence": 0.9},
                {"type": "differentiator", "label": "AI 原生", "confidence": 0.9},
                {"type": "audience", "label": "市场负责人", "confidence": 0.9},
            ],
            "edges": [],
        },
        allowed_source_ids={source_id},
        brand_label="Demo",
        default_source_ids=[source_id],
    )
    facts = sync_facts_from_graph({"industry": "营销科技", "icp": ""}, graph)
    assert facts["products"] == ["产品A"]
    assert facts["pain_points"] == ["获客难"]
    assert facts["differentiators"] == ["AI 原生"]
    assert facts["icp"] == "市场负责人"
    assert facts["industry"] == "营销科技"


def test_parse_relations_json_filters_invalid() -> None:
    graph = parse_relations_json(
        {
            "schema_version": 1,
            "extract_status": "ready",
            "nodes": [{"id": "n1", "type": "product", "label": "A", "confidence": 0.9}],
            "edges": [
                {"id": "e1", "type": "solves", "from": "n1", "to": "missing", "confidence": 0.9},
                {"id": "e2", "type": "bogus", "from": "n1", "to": "n1", "confidence": 0.9},
            ],
        }
    )
    assert len(graph.nodes) == 1
    assert graph.edges == []


def test_extract_subject_knowledge_requires_verified() -> None:
    db = MagicMock()
    knowledge = _knowledge(status="draft")
    db.scalar.return_value = knowledge
    with pytest.raises(KnowledgeNotReadyError):
        extract_subject_knowledge(db, knowledge.subject_id)


@patch("aperix_geo.services.knowledge.graph.extract._call_extract_llm")
def test_extract_subject_knowledge_writes_graph(mock_llm: MagicMock) -> None:
    knowledge = _knowledge()
    source = _source(
        subject_id=knowledge.subject_id,
        tenant_id=knowledge.tenant_id,
        text="Aperix 帮助品牌提升 AI 搜索可见度，解决获客难。",
    )
    mock_llm.return_value = (
        {
            "nodes": [
                {"type": "product", "label": "可见度监测", "source_ids": [str(source.id)], "confidence": 0.9},
                {"type": "pain", "label": "获客难", "source_ids": [str(source.id)], "confidence": 0.85},
            ],
            "edges": [
                {
                    "type": "solves",
                    "from": "可见度监测",
                    "to": "获客难",
                    "source_ids": [str(source.id)],
                    "evidence": "解决获客难",
                    "confidence": 0.8,
                }
            ],
        },
        {"total_tokens": 12},
    )

    db = MagicMock()
    db.scalar.return_value = knowledge
    db.scalars.return_value.all.return_value = [source]

    result = extract_subject_knowledge(db, knowledge.subject_id)

    assert result.extract_status == "ready"
    assert result.node_count >= 2
    assert result.edge_count == 1
    stored = knowledge.relations_json
    assert stored["extract_status"] == "ready"
    assert knowledge.facts_json["pain_points"] == ["获客难"]
    assert knowledge.facts_json["products"] == ["可见度监测"]


@patch("aperix_geo.services.knowledge.graph.extract._call_extract_llm", side_effect=KnowledgeExtractError("boom"))
def test_extract_subject_knowledge_marks_failed(mock_llm: MagicMock) -> None:
    knowledge = _knowledge()
    source = _source(subject_id=knowledge.subject_id, tenant_id=knowledge.tenant_id, text="正文")
    db = MagicMock()
    db.scalar.return_value = knowledge
    db.scalars.return_value.all.return_value = [source]

    with pytest.raises(KnowledgeExtractError):
        extract_subject_knowledge(db, knowledge.subject_id)

    assert knowledge.relations_json["extract_status"] == "failed"
    assert "boom" in knowledge.relations_json["extract_error"]
    assert mock_llm.called
