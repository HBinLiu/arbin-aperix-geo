"""Manage knowledge evidence sources (upload, text, delete)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import KnowledgeSource, Subject, SubjectKnowledge, SubjectType
from aperix_geo.services.knowledge.mutate import KnowledgeNotFoundError, schedule_knowledge_reindex
from aperix_geo.services.knowledge.read import get_subject_knowledge_detail
from aperix_geo.services.setup.upload import extract_upload_text, upload_suffix

MAX_KNOWLEDGE_UPLOAD_FILES = 10
MAX_KNOWLEDGE_UPLOAD_BYTES = 5 * 1024 * 1024
_MANAGEABLE_KINDS = frozenset({"user_input", "upload"})


class KnowledgeSourceNotFoundError(LookupError):
    """Source row not found for subject."""


def _get_knowledge_row(db: Session, subject_id: UUID) -> SubjectKnowledge:
    knowledge = db.scalar(
        select(SubjectKnowledge).where(
            SubjectKnowledge.subject_id == subject_id,
            SubjectKnowledge.deleted.is_(False),
        )
    )
    if knowledge is None:
        raise KnowledgeNotFoundError(f"knowledge not found for subject {subject_id}")
    return knowledge


def _upload_root(settings: Settings | None = None) -> Path:
    cfg = settings or get_settings()
    root = Path(cfg.knowledge_upload_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    base = Path(name).name.strip()
    cleaned = re.sub(r"[^\w.\-()\u4e00-\u9fff]+", "_", base)
    return cleaned[:200] or "upload.bin"


def _assert_not_indexing(knowledge: SubjectKnowledge) -> None:
    if knowledge.index_status == "indexing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="知识库正在索引中，请稍后再编辑。")



def _apply_source_change(
    db: Session,
    *,
    subject: Subject,
    knowledge: SubjectKnowledge,
    user_id: UUID,
) -> None:
    schedule_knowledge_reindex(db, subject=subject, knowledge=knowledge, user_id=user_id)


def _next_sort_order(db: Session, subject_id: UUID) -> int:
    current = db.scalar(
        select(func.max(KnowledgeSource.sort_order)).where(
            KnowledgeSource.subject_id == subject_id,
            KnowledgeSource.deleted.is_(False),
        )
    )
    return int(current or 0) + 1


def ensure_knowledge_for_subject(
    db: Session,
    *,
    subject: Subject,
    user_id: UUID,
) -> SubjectKnowledge:
    try:
        return _get_knowledge_row(db, subject.id)
    except KnowledgeNotFoundError:
        pass

    if subject.type != SubjectType.brand:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="知识库仅支持品牌模式主体。")

    knowledge = SubjectKnowledge(
        tenant_id=subject.tenant_id,
        subject_id=subject.id,
        status="draft",
        version=0,
        index_status="pending",
        indexed_version=0,
        index_error="",
        identity_json={
            "primary_name": str(subject.brand or "").strip(),
            "aliases": list(subject.aliases or []),
            "negative_aliases": [],
            "category": "",
            "disambiguation": "",
            "official_url": str(subject.website_url or "").strip(),
        },
        facts_json={},
        relations_json={},
        narrative_json={},
        voice_json={},
        verified_at=utc_now(),
        verified_by_user_id=user_id,
    )
    db.add(knowledge)
    db.flush()
    return knowledge


def _get_source_row(db: Session, *, subject_id: UUID, source_id: UUID) -> KnowledgeSource:
    source = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.subject_id == subject_id,
            KnowledgeSource.deleted.is_(False),
        )
    )
    if source is None:
        raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")
    return source


def _count_upload_sources(db: Session, subject_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeSource)
            .where(
                KnowledgeSource.subject_id == subject_id,
                KnowledgeSource.kind == "upload",
                KnowledgeSource.deleted.is_(False),
            )
        )
        or 0
    )


def _sync_narrative_overview(knowledge: SubjectKnowledge, text: str) -> None:
    narrative = dict(knowledge.narrative_json or {})
    narrative["overview"] = text.strip()[:4000]
    knowledge.narrative_json = narrative


def upsert_user_input_text(
    db: Session,
    *,
    subject: Subject,
    user_id: UUID,
    text: str,
    title: str = "品牌介绍",
) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文本内容不能为空。")

    knowledge = ensure_knowledge_for_subject(db, subject=subject, user_id=user_id)
    _assert_not_indexing(knowledge)

    source = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.subject_id == subject.id,
            KnowledgeSource.kind == "user_input",
            KnowledgeSource.deleted.is_(False),
        )
    )
    if source is None:
        source = KnowledgeSource(
            tenant_id=subject.tenant_id,
            subject_id=subject.id,
            kind="user_input",
            title=(title or "品牌介绍").strip()[:255] or "品牌介绍",
            uri="",
            raw_text=cleaned,
            char_count=len(cleaned),
            parse_status="ok",
            parse_error="",
            sort_order=0,
        )
        db.add(source)
    else:
        source.title = (title or source.title or "品牌介绍").strip()[:255] or "品牌介绍"
        source.raw_text = cleaned
        source.char_count = len(cleaned)
        source.parse_status = "ok"
        source.parse_error = ""

    _sync_narrative_overview(knowledge, cleaned)
    _apply_source_change(db, subject=subject, knowledge=knowledge, user_id=user_id)
    db.flush()
    return get_subject_knowledge_detail(db, subject.id)


def upload_knowledge_file(
    db: Session,
    *,
    subject: Subject,
    user_id: UUID,
    upload: UploadFile,
) -> dict:
    knowledge = ensure_knowledge_for_subject(db, subject=subject, user_id=user_id)
    _assert_not_indexing(knowledge)

    if _count_upload_sources(db, subject.id) >= MAX_KNOWLEDGE_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多上传 {MAX_KNOWLEDGE_UPLOAD_FILES} 个文件",
        )

    filename = _safe_filename(upload.filename or "upload.txt")
    suffix = upload_suffix(filename)
    if not suffix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .docx、.md、.txt")

    raw = upload.file.read()
    if len(raw) > MAX_KNOWLEDGE_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单文件不能超过 5MB")

    try:
        extracted = extract_upload_text(filename=filename, content=raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_id = uuid.uuid4().hex
    rel_key = f"{subject.tenant_id}/{subject.id}/{file_id}_{filename}"
    dest = _upload_root() / rel_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    mime = (upload.content_type or "").strip() or "application/octet-stream"
    db.add(
        KnowledgeSource(
            tenant_id=subject.tenant_id,
            subject_id=subject.id,
            kind="upload",
            title=filename,
            uri="",
            mime_type=mime,
            file_size=len(raw),
            storage_key=rel_key,
            raw_text=extracted,
            char_count=len(extracted),
            parse_status="ok",
            parse_error="",
            sort_order=_next_sort_order(db, subject.id),
        )
    )
    _apply_source_change(db, subject=subject, knowledge=knowledge, user_id=user_id)
    db.flush()
    return get_subject_knowledge_detail(db, subject.id)


def update_knowledge_source_text(
    db: Session,
    *,
    subject: Subject,
    user_id: UUID,
    source_id: UUID,
    text: str,
    title: str | None = None,
) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文本内容不能为空。")

    knowledge = _get_knowledge_row(db, subject.id)
    _assert_not_indexing(knowledge)
    source = _get_source_row(db, subject_id=subject.id, source_id=source_id)

    if source.kind not in _MANAGEABLE_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该来源不支持编辑。")

    if title is not None:
        source.title = title.strip()[:255] or source.title
    source.raw_text = cleaned
    source.char_count = len(cleaned)
    source.parse_status = "ok"
    source.parse_error = ""

    if source.kind == "user_input":
        _sync_narrative_overview(knowledge, cleaned)

    _apply_source_change(db, subject=subject, knowledge=knowledge, user_id=user_id)
    db.flush()
    return get_subject_knowledge_detail(db, subject.id)


def delete_knowledge_source(
    db: Session,
    *,
    subject: Subject,
    user_id: UUID,
    source_id: UUID,
) -> dict:
    knowledge = _get_knowledge_row(db, subject.id)
    _assert_not_indexing(knowledge)
    source = _get_source_row(db, subject_id=subject.id, source_id=source_id)

    if source.kind not in _MANAGEABLE_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该来源不支持删除。")

    storage_key = str(source.storage_key or "").strip()
    if storage_key:
        path = _upload_root() / storage_key
        if path.is_file():
            path.unlink(missing_ok=True)

    db.delete(source)

    if source.kind == "user_input":
        _sync_narrative_overview(knowledge, "")

    _apply_source_change(db, subject=subject, knowledge=knowledge, user_id=user_id)
    db.flush()
    return get_subject_knowledge_detail(db, subject.id)
