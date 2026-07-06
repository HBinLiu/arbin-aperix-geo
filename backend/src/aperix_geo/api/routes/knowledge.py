"""Subject knowledge base API."""

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.schemas.knowledge import (
    KnowledgeSourceUpdateBody,
    KnowledgeTextSourceBody,
    SubjectKnowledgeDetailOut,
)
from aperix_geo.services.knowledge.mutate import KnowledgeNotFoundError
from aperix_geo.services.knowledge.read import get_subject_knowledge_detail
from aperix_geo.services.knowledge.sources import (
    KnowledgeSourceNotFoundError,
    delete_knowledge_source,
    update_knowledge_source_text,
    upload_knowledge_file,
    upsert_user_input_text,
)

router = APIRouter(prefix="/{subject_id}/knowledge", tags=["knowledge"])


@router.get("", response_model=SubjectKnowledgeDetailOut)
def get_subject_knowledge(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> SubjectKnowledgeDetailOut:
    get_subject_for_user(db, current, subject_id)
    payload = get_subject_knowledge_detail(db, subject_id)
    return SubjectKnowledgeDetailOut(**payload)


@router.post("/sources/text", response_model=SubjectKnowledgeDetailOut)
def upsert_knowledge_text_source(
    subject_id: UUID,
    body: KnowledgeTextSourceBody,
    db: DbSession,
    current: CurrentUser,
) -> SubjectKnowledgeDetailOut:
    subject = get_subject_for_user(db, current, subject_id)
    payload = upsert_user_input_text(
        db,
        subject=subject,
        user_id=current.id,
        text=body.text,
        title=body.title,
    )
    db.commit()
    return SubjectKnowledgeDetailOut(**payload)


@router.post("/sources/upload", response_model=SubjectKnowledgeDetailOut)
def upload_knowledge_source_file(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
    file: UploadFile = File(...),
) -> SubjectKnowledgeDetailOut:
    subject = get_subject_for_user(db, current, subject_id)
    payload = upload_knowledge_file(db, subject=subject, user_id=current.id, upload=file)
    db.commit()
    return SubjectKnowledgeDetailOut(**payload)


@router.patch("/sources/{source_id}", response_model=SubjectKnowledgeDetailOut)
def patch_knowledge_source(
    subject_id: UUID,
    source_id: UUID,
    body: KnowledgeSourceUpdateBody,
    db: DbSession,
    current: CurrentUser,
) -> SubjectKnowledgeDetailOut:
    subject = get_subject_for_user(db, current, subject_id)
    try:
        payload = update_knowledge_source_text(
            db,
            subject=subject,
            user_id=current.id,
            source_id=source_id,
            text=body.text,
            title=body.title,
        )
    except KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未建立知识库。") from exc
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资料来源不存在。") from exc
    db.commit()
    return SubjectKnowledgeDetailOut(**payload)


@router.delete("/sources/{source_id}", response_model=SubjectKnowledgeDetailOut)
def delete_knowledge_source_route(
    subject_id: UUID,
    source_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> SubjectKnowledgeDetailOut:
    subject = get_subject_for_user(db, current, subject_id)
    try:
        payload = delete_knowledge_source(db, subject=subject, user_id=current.id, source_id=source_id)
    except KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未建立知识库。") from exc
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资料来源不存在。") from exc
    db.commit()
    return SubjectKnowledgeDetailOut(**payload)
