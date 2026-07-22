"""Extract brand knowledge graph from verified sources via LLM."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from aperix_geo.db.base import utc_now
from aperix_geo.db.models import KnowledgeSource, SubjectKnowledge
from aperix_geo.services.knowledge.exceptions import KnowledgeExtractError, KnowledgeNotReadyError
from aperix_geo.services.knowledge.graph.sync_facts import sync_facts_from_graph
from aperix_geo.services.knowledge.graph.schema import (
    ExtractStatus,
    KnowledgeGraph,
    empty_graph,
    normalize_llm_graph,
    parse_relations_json,
)
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    KNOWLEDGE_GRAPH_EXTRACT_SYSTEM,
    KNOWLEDGE_GRAPH_EXTRACT_USER_SUFFIX,
)
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

# Soft cap on corpus chars sent to the LLM (approx. token budget).
_MAX_CORPUS_CHARS = 48_000
_MAX_SOURCE_CHARS = 12_000


@dataclass(frozen=True, slots=True)
class ExtractSubjectResult:
    subject_id: UUID
    knowledge_version: int
    node_count: int
    edge_count: int
    extract_status: str
    llm_usage: dict[str, Any] = field(default_factory=dict)


def mark_extract_pending(knowledge: SubjectKnowledge) -> None:
    """Set relations_json extract_status=pending without clearing a previous ready graph."""
    raw = getattr(knowledge, "relations_json", None) or {}
    graph = parse_relations_json(raw)
    graph.extract_status = ExtractStatus.pending
    graph.extract_error = ""
    knowledge.relations_json = graph.to_storage()
    try:
        flag_modified(knowledge, "relations_json")
    except Exception:
        # SimpleNamespace / non-ORM stand-ins used in unit tests.
        pass


def extract_subject_knowledge(db: Session, subject_id: UUID) -> ExtractSubjectResult:
    """
    Run LLM graph extraction for a verified subject knowledge row.
    Writes relations_json and projects into facts_json.
    """
    knowledge = db.scalar(
        select(SubjectKnowledge).where(
            SubjectKnowledge.subject_id == subject_id,
            SubjectKnowledge.deleted.is_(False),
        )
    )
    if knowledge is None:
        raise KnowledgeNotReadyError(f"subject knowledge not found: {subject_id}")
    if knowledge.status != "verified":
        raise KnowledgeNotReadyError(
            f"subject knowledge status must be verified, got {knowledge.status!r}"
        )

    mark_extract_pending(knowledge)
    db.flush()

    try:
        result = _extract_verified_knowledge(db, knowledge)
        db.flush()
        return result
    except Exception as exc:
        graph = parse_relations_json(knowledge.relations_json)
        graph.extract_status = ExtractStatus.failed
        graph.extract_error = str(exc)[:2000]
        knowledge.relations_json = graph.to_storage()
        flag_modified(knowledge, "relations_json")
        db.flush()
        if isinstance(exc, KnowledgeExtractError):
            raise
        raise KnowledgeExtractError(str(exc)) from exc


def _extract_verified_knowledge(db: Session, knowledge: SubjectKnowledge) -> ExtractSubjectResult:
    sources = list(
        db.scalars(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.subject_id == knowledge.subject_id,
                KnowledgeSource.deleted.is_(False),
                KnowledgeSource.parse_status == "ok",
            )
            .order_by(KnowledgeSource.sort_order.asc(), KnowledgeSource.created_at.asc())
        ).all()
    )
    usable = [s for s in sources if (s.raw_text or "").strip()]
    if not usable:
        graph = empty_graph(status=ExtractStatus.skipped, error="no usable sources")
        graph.extracted_at = utc_now().isoformat()
        knowledge.relations_json = graph.to_storage()
        flag_modified(knowledge, "relations_json")
        return ExtractSubjectResult(
            subject_id=knowledge.subject_id,
            knowledge_version=knowledge.version,
            node_count=0,
            edge_count=0,
            extract_status=ExtractStatus.skipped.value,
        )

    identity = dict(knowledge.identity_json or {})
    brand_label = str(identity.get("primary_name") or "").strip() or "品牌"
    brand_aliases = [
        str(a).strip()
        for a in (identity.get("aliases") or [])
        if str(a).strip()
    ]
    allowed_ids = {str(s.id) for s in usable}
    corpus_parts, default_source_ids = _build_corpus(usable)

    user_payload = {
        "brand": {
            "primary_name": brand_label,
            "aliases": brand_aliases,
            "category": str(identity.get("category") or "").strip(),
        },
        "sources": corpus_parts,
        "allowed_node_types": [
            "brand",
            "product",
            "audience",
            "pain",
            "differentiator",
            "competitor",
            "scenario",
            "proof",
        ],
        "allowed_edge_types": [
            "offers",
            "serves",
            "solves",
            "differentiates_by",
            "competes_with",
            "used_in",
            "part_of",
            "supported_by",
        ],
    }

    try:
        data, usage = _call_extract_llm(user_payload)
    except LLMProviderError as exc:
        raise KnowledgeExtractError(f"graph extract LLM error: {exc}") from exc
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise KnowledgeExtractError(f"graph extract parse error: {exc}") from exc

    now = utc_now()
    graph = normalize_llm_graph(
        data,
        allowed_source_ids=allowed_ids,
        brand_label=brand_label,
        brand_aliases=brand_aliases,
        default_source_ids=default_source_ids,
        extracted_at=now,
    )
    knowledge.relations_json = graph.to_storage()
    flag_modified(knowledge, "relations_json")

    knowledge.facts_json = sync_facts_from_graph(dict(knowledge.facts_json or {}), graph)
    flag_modified(knowledge, "facts_json")

    logger.info(
        "knowledge graph extracted subject=%s version=%s nodes=%s edges=%s",
        knowledge.subject_id,
        knowledge.version,
        len(graph.nodes),
        len(graph.edges),
    )
    return ExtractSubjectResult(
        subject_id=knowledge.subject_id,
        knowledge_version=knowledge.version,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        extract_status=graph.extract_status.value,
        llm_usage=usage,
    )


def _build_corpus(sources: list[KnowledgeSource]) -> tuple[list[dict[str, Any]], list[str]]:
    parts: list[dict[str, Any]] = []
    default_ids: list[str] = []
    remaining = _MAX_CORPUS_CHARS
    for source in sources:
        if remaining <= 0:
            break
        text = (source.raw_text or "").strip()
        if not text:
            continue
        clipped = text[: min(_MAX_SOURCE_CHARS, remaining)]
        remaining -= len(clipped)
        sid = str(source.id)
        default_ids.append(sid)
        parts.append(
            {
                "source_id": sid,
                "kind": source.kind,
                "title": source.title,
                "text": clipped,
            }
        )
    return parts, default_ids


def _call_extract_llm(user_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    text, usage, latency_ms = chat_completion(
        [
            {"role": "system", "content": KNOWLEDGE_GRAPH_EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n\n"
                    f"{KNOWLEDGE_GRAPH_EXTRACT_USER_SUFFIX}"
                ),
            },
        ],
        temperature=0.1,
        json_mode=True,
    )
    data = extract_json_object(text)
    if not isinstance(data, dict):
        raise ValueError("extract response is not a JSON object")
    usage = dict(usage or {})
    usage["latency_ms"] = latency_ms
    return data, usage


def graph_for_api(knowledge: SubjectKnowledge | None) -> dict[str, Any] | None:
    if knowledge is None:
        return None
    return parse_relations_json(knowledge.relations_json).to_api()
