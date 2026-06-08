"""Topics under a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Subject, Topic
from aperix_geo.schemas.catalog import TopicCreate, TopicOut

router = APIRouter(tags=["topics"])


@router.get("/subjects/{subject_id}/topics", response_model=list[TopicOut])
def list_topics(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> list[Topic]:
    get_subject_for_user(db, current, subject_id)
    return list(db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all())


@router.post("/subjects/{subject_id}/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(
    subject_id: UUID,
    body: TopicCreate,
    db: DbSession,
    current: CurrentUser,
) -> Topic:
    get_subject_for_user(db, current, subject_id)
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
    get_subject_for_user(db, current, subject_id)
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
    get_subject_for_user(db, current, subject_id)
    t = db.get(Topic, topic_id)
    if not t or t.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(t)
    db.commit()
