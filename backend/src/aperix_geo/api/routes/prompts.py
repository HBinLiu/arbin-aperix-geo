"""Prompts under a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.db.models import Prompt, Subject, Topic, User
from aperix_geo.schemas.catalog import PromptCreate, PromptOut, PromptUpdate
from aperix_geo.utils.text import prompt_text_hash

router = APIRouter(tags=["prompts"])


def _sub(db: Session, user: User, subject_id: UUID) -> Subject:
    s = db.get(Subject, subject_id)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return s


@router.get("/subjects/{subject_id}/prompts", response_model=list[PromptOut])
def list_prompts(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> list[Prompt]:
    _sub(db, current, subject_id)
    return list(db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all())


@router.post("/subjects/{subject_id}/prompts", response_model=PromptOut, status_code=status.HTTP_201_CREATED)
def create_prompt(
    subject_id: UUID,
    body: PromptCreate,
    db: DbSession,
    current: CurrentUser,
) -> Prompt:
    _sub(db, current, subject_id)
    topic = db.get(Topic, body.topic_id)
    if not topic or topic.subject_id != subject_id:
        raise HTTPException(status_code=400, detail="Invalid topic_id for this subject")
    th = prompt_text_hash(body.text)
    dup = db.execute(select(Prompt).where(Prompt.subject_id == subject_id, Prompt.text_hash == th)).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Duplicate prompt text for this subject")
    p = Prompt(
        subject_id=subject_id,
        topic_id=body.topic_id,
        text=body.text.strip(),
        text_hash=th,
        enabled=body.enabled,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/subjects/{subject_id}/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(
    subject_id: UUID,
    prompt_id: UUID,
    body: PromptUpdate,
    db: DbSession,
    current: CurrentUser,
) -> Prompt:
    _sub(db, current, subject_id)
    p = db.get(Prompt, prompt_id)
    if not p or p.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if body.topic_id is not None:
        topic = db.get(Topic, body.topic_id)
        if not topic or topic.subject_id != subject_id:
            raise HTTPException(status_code=400, detail="Invalid topic_id")
        p.topic_id = body.topic_id
    if body.text is not None:
        p.text = body.text.strip()
        p.text_hash = prompt_text_hash(p.text)
    if body.enabled is not None:
        p.enabled = body.enabled
    db.commit()
    db.refresh(p)
    return p


@router.delete("/subjects/{subject_id}/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(
    subject_id: UUID,
    prompt_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    _sub(db, current, subject_id)
    p = db.get(Prompt, prompt_id)
    if not p or p.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(p)
    db.commit()
