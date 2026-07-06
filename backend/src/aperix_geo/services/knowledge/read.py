"""Read subject knowledge for dashboard UI."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import KnowledgeChunk, KnowledgeSource, SubjectKnowledge

_RAW_TEXT_PREVIEW_LEN = 400


def _source_row(source: KnowledgeSource) -> dict:
    text = source.raw_text or ""
    preview = text[:_RAW_TEXT_PREVIEW_LEN]
    if len(text) > _RAW_TEXT_PREVIEW_LEN:
        preview = preview.rstrip() + "…"
    return {
        "id": source.id,
        "kind": source.kind,
        "title": source.title,
        "uri": source.uri,
        "mime_type": source.mime_type,
        "file_size": source.file_size,
        "char_count": source.char_count,
        "parse_status": source.parse_status,
        "parse_error": source.parse_error,
        "sort_order": source.sort_order,
        "raw_text_preview": preview,
        "raw_text": text if source.kind == "user_input" else "",
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _knowledge_meta(knowledge: SubjectKnowledge) -> dict:
    return {
        "id": knowledge.id,
        "subject_id": knowledge.subject_id,
        "status": knowledge.status,
        "version": knowledge.version,
        "index_status": knowledge.index_status,
        "indexed_version": knowledge.indexed_version,
        "index_error": knowledge.index_error,
        "verified_at": knowledge.verified_at,
        "updated_at": knowledge.updated_at,
    }


def get_subject_knowledge_detail(db: Session, subject_id: UUID) -> dict:
    knowledge = db.scalar(
        select(SubjectKnowledge).where(
            SubjectKnowledge.subject_id == subject_id,
            SubjectKnowledge.deleted.is_(False),
        )
    )
    sources = list(
        db.scalars(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.subject_id == subject_id,
                KnowledgeSource.deleted.is_(False),
            )
            .order_by(KnowledgeSource.sort_order.asc(), KnowledgeSource.created_at.asc())
        ).all()
    )

    if knowledge is None:
        return {
            "knowledge": None,
            "sources": [_source_row(row) for row in sources],
            "chunk_count": 0,
        }

    chunk_count = int(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeChunk)
            .where(
                KnowledgeChunk.subject_id == subject_id,
                KnowledgeChunk.knowledge_version == knowledge.version,
                KnowledgeChunk.deleted.is_(False),
            )
        )
        or 0
    )

    return {
        "knowledge": _knowledge_meta(knowledge),
        "sources": [_source_row(row) for row in sources],
        "chunk_count": chunk_count,
    }
