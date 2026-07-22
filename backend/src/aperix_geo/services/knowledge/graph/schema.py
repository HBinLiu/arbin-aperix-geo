"""Brand knowledge graph schema (relations_json v1)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = 1
MIN_EDGE_CONFIDENCE = 0.6
MAX_EVIDENCE_CHARS = 120
MAX_LABEL_CHARS = 80


class NodeType(StrEnum):
    brand = "brand"
    product = "product"
    audience = "audience"
    pain = "pain"
    differentiator = "differentiator"
    competitor = "competitor"
    scenario = "scenario"
    proof = "proof"


class EdgeType(StrEnum):
    offers = "offers"
    serves = "serves"
    solves = "solves"
    differentiates_by = "differentiates_by"
    competes_with = "competes_with"
    used_in = "used_in"
    part_of = "part_of"
    supported_by = "supported_by"


class ExtractStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    failed = "failed"
    skipped = "skipped"


_EDGE_LABELS: dict[EdgeType, str] = {
    EdgeType.offers: "提供",
    EdgeType.serves: "服务",
    EdgeType.solves: "解决",
    EdgeType.differentiates_by: "差异化",
    EdgeType.competes_with: "竞对",
    EdgeType.used_in: "用于",
    EdgeType.part_of: "属于",
    EdgeType.supported_by: "佐证",
}

_NODE_TYPE_SET = frozenset(t.value for t in NodeType)
_EDGE_TYPE_SET = frozenset(t.value for t in EdgeType)


def stable_node_id(node_type: str, label: str) -> str:
    key = f"{node_type}:{_normalize_label(label).lower()}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"n_{node_type}_{digest}"


def stable_edge_id(edge_type: str, from_id: str, to_id: str) -> str:
    key = f"{edge_type}:{from_id}:{to_id}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"e_{edge_type}_{digest}"


def _normalize_label(label: str) -> str:
    text = re.sub(r"\s+", " ", str(label or "").strip())
    return text[:MAX_LABEL_CHARS]


def _clamp_confidence(value: Any, default: float = 0.7) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        conf = default
    return max(0.0, min(1.0, conf))


def _as_source_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        try:
            out.append(str(UUID(text)))
        except ValueError:
            continue
    return list(dict.fromkeys(out))


class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str
    aliases: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.7

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        text = _normalize_label(value)
        if not text:
            raise ValueError("label required")
        return text


class GraphEdge(BaseModel):
    id: str
    type: EdgeType
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    label: str = ""
    source_ids: list[str] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = 0.7

    model_config = {"populate_by_name": True}


class KnowledgeGraph(BaseModel):
    schema_version: int = SCHEMA_VERSION
    extract_status: ExtractStatus = ExtractStatus.pending
    extract_error: str = ""
    extracted_at: str = ""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def to_storage(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "extract_status": self.extract_status.value,
            "extract_error": self.extract_error[:2000],
            "extracted_at": self.extracted_at,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type.value,
                    "label": node.label,
                    "aliases": list(node.aliases),
                    "source_ids": list(node.source_ids),
                    "confidence": node.confidence,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "type": edge.type.value,
                    "from": edge.from_id,
                    "to": edge.to_id,
                    "label": edge.label or _EDGE_LABELS.get(edge.type, edge.type.value),
                    "source_ids": list(edge.source_ids),
                    "evidence": edge.evidence[:MAX_EVIDENCE_CHARS],
                    "confidence": edge.confidence,
                }
                for edge in self.edges
            ],
        }

    def to_api(self, *, min_edge_confidence: float = MIN_EDGE_CONFIDENCE) -> dict[str, Any] | None:
        if self.extract_status == ExtractStatus.pending and not self.nodes:
            return {
                "schema_version": self.schema_version,
                "extract_status": self.extract_status.value,
                "extract_error": self.extract_error,
                "extracted_at": self.extracted_at,
                "nodes": [],
                "edges": [],
            }
        nodes = [
            {
                "id": node.id,
                "type": node.type.value,
                "label": node.label,
                "aliases": list(node.aliases),
                "source_ids": list(node.source_ids),
                "confidence": node.confidence,
            }
            for node in self.nodes
        ]
        node_ids = {node["id"] for node in nodes}
        edges = []
        for edge in self.edges:
            if edge.confidence < min_edge_confidence:
                continue
            if edge.from_id not in node_ids or edge.to_id not in node_ids:
                continue
            edges.append(
                {
                    "id": edge.id,
                    "type": edge.type.value,
                    "from": edge.from_id,
                    "to": edge.to_id,
                    "label": edge.label or _EDGE_LABELS.get(edge.type, edge.type.value),
                    "source_ids": list(edge.source_ids),
                    "evidence": edge.evidence[:MAX_EVIDENCE_CHARS],
                    "confidence": edge.confidence,
                }
            )
        return {
            "schema_version": self.schema_version,
            "extract_status": self.extract_status.value,
            "extract_error": self.extract_error,
            "extracted_at": self.extracted_at,
            "nodes": nodes,
            "edges": edges,
        }


def empty_graph(*, status: ExtractStatus = ExtractStatus.pending, error: str = "") -> KnowledgeGraph:
    return KnowledgeGraph(extract_status=status, extract_error=error)


def parse_relations_json(raw: Any) -> KnowledgeGraph:
    if not isinstance(raw, dict) or not raw:
        return empty_graph()
    status_raw = str(raw.get("extract_status") or ExtractStatus.pending.value)
    try:
        status = ExtractStatus(status_raw)
    except ValueError:
        status = ExtractStatus.pending

    nodes: list[GraphNode] = []
    for item in raw.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        node_type = str(item.get("type") or "").strip()
        label = _normalize_label(str(item.get("label") or ""))
        if node_type not in _NODE_TYPE_SET or not label:
            continue
        node_id = str(item.get("id") or "").strip() or stable_node_id(node_type, label)
        aliases = [
            _normalize_label(a)
            for a in (item.get("aliases") or [])
            if _normalize_label(str(a))
        ]
        nodes.append(
            GraphNode(
                id=node_id,
                type=NodeType(node_type),
                label=label,
                aliases=list(dict.fromkeys(aliases)),
                source_ids=_as_source_ids(item.get("source_ids")),
                confidence=_clamp_confidence(item.get("confidence")),
            )
        )

    node_ids = {node.id for node in nodes}
    edges: list[GraphEdge] = []
    for item in raw.get("edges") or []:
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "").strip()
        from_id = str(item.get("from") or "").strip()
        to_id = str(item.get("to") or "").strip()
        if edge_type not in _EDGE_TYPE_SET or from_id not in node_ids or to_id not in node_ids:
            continue
        evidence = re.sub(r"\s+", " ", str(item.get("evidence") or "").strip())[:MAX_EVIDENCE_CHARS]
        label = str(item.get("label") or "").strip() or _EDGE_LABELS[EdgeType(edge_type)]
        edge_id = str(item.get("id") or "").strip() or stable_edge_id(edge_type, from_id, to_id)
        edges.append(
            GraphEdge(
                id=edge_id,
                type=EdgeType(edge_type),
                from_id=from_id,
                to_id=to_id,
                label=label[:40],
                source_ids=_as_source_ids(item.get("source_ids")),
                evidence=evidence,
                confidence=_clamp_confidence(item.get("confidence")),
            )
        )

    return KnowledgeGraph(
        schema_version=int(raw.get("schema_version") or SCHEMA_VERSION),
        extract_status=status,
        extract_error=str(raw.get("extract_error") or "")[:2000],
        extracted_at=str(raw.get("extracted_at") or ""),
        nodes=nodes,
        edges=edges,
    )


def normalize_llm_graph(
    data: dict[str, Any],
    *,
    allowed_source_ids: set[str],
    brand_label: str,
    brand_aliases: list[str] | None = None,
    default_source_ids: list[str] | None = None,
    extracted_at: datetime | None = None,
) -> KnowledgeGraph:
    """Validate LLM JSON into a KnowledgeGraph; always ensure a brand hub node."""
    default_sources = [sid for sid in (default_source_ids or []) if sid in allowed_source_ids]
    brand = _normalize_label(brand_label) or "品牌"
    brand_id = stable_node_id(NodeType.brand.value, brand)

    nodes_by_id: dict[str, GraphNode] = {}
    for item in data.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        node_type = str(item.get("type") or "").strip()
        label = _normalize_label(str(item.get("label") or ""))
        if node_type not in _NODE_TYPE_SET or not label:
            continue
        if node_type == NodeType.brand.value:
            # Keep a single brand hub aligned to identity.
            continue
        node_id = stable_node_id(node_type, label)
        source_ids = [sid for sid in _as_source_ids(item.get("source_ids")) if sid in allowed_source_ids]
        if not source_ids:
            source_ids = list(default_sources)
        aliases = [
            _normalize_label(a)
            for a in (item.get("aliases") or [])
            if _normalize_label(str(a)) and _normalize_label(str(a)).lower() != label.lower()
        ]
        prev = nodes_by_id.get(node_id)
        conf = _clamp_confidence(item.get("confidence"))
        if prev is None or conf > prev.confidence:
            nodes_by_id[node_id] = GraphNode(
                id=node_id,
                type=NodeType(node_type),
                label=label,
                aliases=list(dict.fromkeys([*(prev.aliases if prev else []), *aliases])),
                source_ids=list(dict.fromkeys([*(prev.source_ids if prev else []), *source_ids])),
                confidence=conf,
            )

    nodes_by_id[brand_id] = GraphNode(
        id=brand_id,
        type=NodeType.brand,
        label=brand,
        aliases=[
            _normalize_label(a)
            for a in (brand_aliases or [])
            if _normalize_label(str(a)) and _normalize_label(str(a)).lower() != brand.lower()
        ],
        source_ids=list(default_sources),
        confidence=1.0,
    )

    # Remap any LLM brand node ids / labels to hub.
    label_to_id = {node.label.lower(): node.id for node in nodes_by_id.values()}
    label_to_id[brand.lower()] = brand_id
    for alias in brand_aliases or []:
        alias_n = _normalize_label(alias)
        if alias_n:
            label_to_id[alias_n.lower()] = brand_id

    edges_by_id: dict[str, GraphEdge] = {}
    for item in data.get("edges") or []:
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "").strip()
        if edge_type not in _EDGE_TYPE_SET:
            continue
        from_ref = str(item.get("from") or item.get("from_label") or "").strip()
        to_ref = str(item.get("to") or item.get("to_label") or "").strip()
        from_id = _resolve_endpoint(from_ref, nodes_by_id, label_to_id, brand_id=brand_id)
        to_id = _resolve_endpoint(to_ref, nodes_by_id, label_to_id, brand_id=brand_id)
        if not from_id or not to_id or from_id == to_id:
            continue
        if from_id not in nodes_by_id or to_id not in nodes_by_id:
            continue
        source_ids = [sid for sid in _as_source_ids(item.get("source_ids")) if sid in allowed_source_ids]
        if not source_ids:
            source_ids = list(default_sources)
        evidence = re.sub(r"\s+", " ", str(item.get("evidence") or "").strip())[:MAX_EVIDENCE_CHARS]
        conf = _clamp_confidence(item.get("confidence"))
        edge_id = stable_edge_id(edge_type, from_id, to_id)
        label = str(item.get("label") or "").strip() or _EDGE_LABELS[EdgeType(edge_type)]
        prev = edges_by_id.get(edge_id)
        if prev is None or conf > prev.confidence:
            edges_by_id[edge_id] = GraphEdge(
                id=edge_id,
                type=EdgeType(edge_type),
                from_id=from_id,
                to_id=to_id,
                label=label[:40],
                source_ids=list(dict.fromkeys([*(prev.source_ids if prev else []), *source_ids])),
                evidence=evidence or (prev.evidence if prev else ""),
                confidence=conf,
            )

    ts = extracted_at.isoformat() if extracted_at else ""
    return KnowledgeGraph(
        schema_version=SCHEMA_VERSION,
        extract_status=ExtractStatus.ready,
        extract_error="",
        extracted_at=ts,
        nodes=list(nodes_by_id.values()),
        edges=list(edges_by_id.values()),
    )


def _resolve_endpoint(
    ref: str,
    nodes_by_id: dict[str, GraphNode],
    label_to_id: dict[str, str],
    *,
    brand_id: str,
) -> str | None:
    text = ref.strip()
    if not text:
        return None
    if text in nodes_by_id:
        return text
    if text.startswith("n_brand"):
        return brand_id
    lowered = _normalize_label(text).lower()
    if lowered in label_to_id:
        return label_to_id[lowered]
    return None
