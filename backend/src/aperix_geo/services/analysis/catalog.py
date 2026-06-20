"""Subject-scoped catalog lookups shared by analysis builders."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Topic


def load_topic_prompt_catalog(
    db: Session,
    subject_id: UUID,
) -> tuple[dict[UUID, Topic], dict[UUID, Prompt], dict[UUID, UUID]]:
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    }
    prompt_to_topic = {pid: p.topic_id for pid, p in prompts.items()}
    return topics, prompts, prompt_to_topic
