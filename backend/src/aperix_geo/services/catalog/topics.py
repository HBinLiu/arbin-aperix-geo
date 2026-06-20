"""Cached subject topic list."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Topic
from aperix_geo.schemas.catalog import TopicOut
from aperix_geo.services.catalog.cache import topics_cache_get, topics_cache_set


def list_subject_topics(db: Session, *, subject_id: UUID) -> list[TopicOut]:
    cached = topics_cache_get(subject_id)
    if cached is not None:
        return [TopicOut.model_validate(item) for item in cached["topics"]]

    rows = list(db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all())
    topics = [TopicOut.model_validate(row) for row in rows]
    topics_cache_set(
        subject_id,
        {"topics": [topic.model_dump(mode="json") for topic in topics]},
    )
    return topics
