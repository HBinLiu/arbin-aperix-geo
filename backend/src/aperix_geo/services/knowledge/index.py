"""Index verified knowledge sources into pgvector chunks."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import KnowledgeChunk, KnowledgeSource, SubjectKnowledge
from aperix_geo.services.knowledge.chunk import TextChunk, chunk_text, estimate_token_count
from aperix_geo.services.knowledge.embed import embed_texts
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError, KnowledgeNotReadyError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IndexSubjectResult:
    subject_id: UUID
    knowledge_version: int
    chunks_created: int
    chunks_skipped: int
    sources_indexed: int
    embedding_usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _PendingChunk:
    source: KnowledgeSource
    piece: TextChunk
    content_hash: str


def index_subject_knowledge(
    db: Session,
    subject_id: UUID,
    *,
    settings: Settings | None = None,
) -> IndexSubjectResult:
    """
    Index all eligible sources for a verified subject knowledge row.
    Inserts new chunk rows for the current knowledge.version; older versions are retained.
    """
    cfg = settings or get_settings()
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

    knowledge.index_status = "indexing"
    knowledge.index_error = ""
    db.flush()

    try:
        result = _index_verified_knowledge(db, knowledge, settings=cfg)
        knowledge.index_status = "indexed"
        knowledge.indexed_version = knowledge.version
        knowledge.index_error = ""
        db.flush()
        return result
    except Exception as exc:
        knowledge.index_status = "failed"
        knowledge.index_error = str(exc)[:2000]
        db.flush()
        if isinstance(exc, KnowledgeIndexError):
            raise
        raise KnowledgeIndexError(str(exc)) from exc


def _index_verified_knowledge(
    db: Session,
    knowledge: SubjectKnowledge,
    *,
    settings: Settings,
) -> IndexSubjectResult:
    sources = list(
        db.scalars(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.subject_id == knowledge.subject_id,
                KnowledgeSource.deleted.is_(False),
                KnowledgeSource.parse_status == "ok",
            )
            .order_by(KnowledgeSource.sort_order.asc(), KnowledgeSource.created_at.asc())
        )
    )

    existing_hashes = set(
        db.scalars(
            select(KnowledgeChunk.content_hash).where(
                KnowledgeChunk.subject_id == knowledge.subject_id,
                KnowledgeChunk.knowledge_version == knowledge.version,
                KnowledgeChunk.deleted.is_(False),
                KnowledgeChunk.content_hash != "",
            )
        )
    )

    pending: list[_PendingChunk] = []
    sources_with_text = 0
    skipped = 0

    for source in sources:
        raw = source.raw_text.strip()
        if not raw:
            continue
        sources_with_text += 1
        pieces = chunk_text(
            raw,
            chunk_size=settings.knowledge_chunk_size,
            overlap=settings.knowledge_chunk_overlap,
            max_chunks=settings.knowledge_chunk_max_per_source,
        )
        for piece in pieces:
            content_hash = _content_hash(piece.text)
            if content_hash in existing_hashes:
                skipped += 1
                continue
            existing_hashes.add(content_hash)
            pending.append(_PendingChunk(source=source, piece=piece, content_hash=content_hash))

    if not pending:
        return IndexSubjectResult(
            subject_id=knowledge.subject_id,
            knowledge_version=knowledge.version,
            chunks_created=0,
            chunks_skipped=skipped,
            sources_indexed=sources_with_text,
        )

    usage_total: dict[str, Any] = {}
    created = 0
    batch_size = max(1, settings.embedding_batch_size)

    for offset in range(0, len(pending), batch_size):
        batch = pending[offset : offset + batch_size]
        vectors, usage = embed_texts([item.piece.text for item in batch], settings=settings)
        _merge_usage(usage_total, usage)

        for item, vector in zip(batch, vectors, strict=True):
            source = item.source
            piece = item.piece
            db.add(
                KnowledgeChunk(
                    id=uuid.uuid4(),
                    tenant_id=knowledge.tenant_id,
                    subject_id=knowledge.subject_id,
                    source_id=source.id,
                    knowledge_version=knowledge.version,
                    chunk_index=piece.chunk_index,
                    content_text=piece.text,
                    content_hash=item.content_hash,
                    char_start=piece.char_start,
                    char_end=piece.char_end,
                    token_count=estimate_token_count(piece.text),
                    embedding=vector,
                    embedding_model=settings.embedding_model,
                    metadata_json={
                        "source_kind": source.kind,
                        "file_name": source.title if source.kind == "upload" else "",
                    },
                )
            )
            created += 1

    logger.info(
        "indexed subject=%s version=%s chunks=%s skipped=%s sources=%s",
        knowledge.subject_id,
        knowledge.version,
        created,
        skipped,
        sources_with_text,
    )
    return IndexSubjectResult(
        subject_id=knowledge.subject_id,
        knowledge_version=knowledge.version,
        chunks_created=created,
        chunks_skipped=skipped,
        sources_indexed=sources_with_text,
        embedding_usage=usage_total,
    )


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge_usage(total: dict[str, Any], batch: dict[str, Any]) -> None:
    for key, value in batch.items():
        if key == "latency_ms" and isinstance(value, int):
            total["latency_ms"] = int(total.get("latency_ms", 0)) + value
        elif isinstance(value, (int, float)):
            total[key] = type(value)(total.get(key, 0)) + value
        else:
            total[key] = value
