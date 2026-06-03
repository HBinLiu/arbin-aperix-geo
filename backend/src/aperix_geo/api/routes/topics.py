"""Topics under a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.db.models import Subject, Topic, User
from aperix_geo.schemas.catalog import TopicCreate, TopicOut

router = APIRouter(tags=["topics"])


def _sub(db: Session, user: User, subject_id: UUID) -> Subject:
    s = db.get(Subject, subject_id)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return s


@router.get("/subjects/{subject_id}/topics", response_model=list[TopicOut])
def list_topics(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> list[Topic]:
    _sub(db, current, subject_id)
    return list(db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all())


@router.post("/subjects/{subject_id}/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(
    subject_id: UUID,
    body: TopicCreate,
    db: DbSession,
    current: CurrentUser,
) -> Topic:
    _sub(db, current, subject_id)
    t = Topic(subject_id=subject_id, name=body.name.strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/subjects/{subject_id}/topics/{topic_id}", response_model=TopicOut)
def update_topic(
    subject_id: UUID,
    topic_id: UUID,
    body: TopicCreate,
    db: DbSession,
    current: CurrentUser,
) -> Topic:
    _sub(db, current, subject_id)
    t = db.get(Topic, topic_id)
    if not t or t.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    t.name = body.name.strip()
    db.commit()
    db.refresh(t)
    return t


@router.delete("/subjects/{subject_id}/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    subject_id: UUID,
    topic_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    _sub(db, current, subject_id)
    t = db.get(Topic, topic_id)
    if not t or t.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(t)
    db.commit()
