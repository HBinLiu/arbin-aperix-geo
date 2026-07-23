"""Upsert materialized prompt fan-out candidates from sampling search queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.base import utc_now
from aperix_geo.db.models import Prompt, SubjectPromptFanout, ZERO_UUID
from aperix_geo.services.providers._helpers import dedupe_search_queries
from aperix_geo.services.prompts.persist import PROMPT_KIND_FANOUT, PROMPT_KIND_ROOT
from aperix_geo.services.sampling.fanout import (
    normalize_fanout_query_key,
    platform_exposes_search_queries,
)

FANOUT_STATUS_PENDING = "pending"
FANOUT_STATUS_PROMOTED = "promoted"
FANOUT_STATUS_DISMISSED = "dismissed"


def upsert_prompt_fanouts(
    db: Session,
    *,
    subject_id: UUID,
    parent_prompt_id: UUID,
    topic_id: UUID,
    platform: str,
    queries: list[str] | tuple[str, ...],
    seen_at: datetime | None = None,
) -> int:
    """Increment frequency / platform_counts for each expanded query. Returns upserted count."""
    platform_id = str(platform or "").strip().lower()
    if not platform_exposes_search_queries(platform_id):
        return 0
    expanded = list(dedupe_search_queries(list(queries)))
    if not expanded:
        return 0

    now = seen_at or utc_now()
    upserted = 0
    for query_text in expanded:
        key = normalize_fanout_query_key(query_text)
        if not key:
            continue
        row = db.execute(
            select(SubjectPromptFanout).where(
                SubjectPromptFanout.subject_id == subject_id,
                SubjectPromptFanout.parent_prompt_id == parent_prompt_id,
                SubjectPromptFanout.query_key == key,
                SubjectPromptFanout.deleted.is_(False),
            )
        ).scalar_one_or_none()
        if row is None:
            counts: dict[str, Any] = {platform_id: 1} if platform_id else {}
            db.add(
                SubjectPromptFanout(
                    subject_id=subject_id,
                    parent_prompt_id=parent_prompt_id,
                    topic_id=topic_id,
                    query_text=query_text,
                    query_key=key,
                    frequency=1,
                    platform_counts=counts,
                    first_seen_at=now,
                    last_seen_at=now,
                    status=FANOUT_STATUS_PENDING,
                    promoted_prompt_id=ZERO_UUID,
                )
            )
            upserted += 1
            continue

        row.frequency = int(row.frequency or 0) + 1
        counts = dict(row.platform_counts or {})
        if platform_id:
            counts[platform_id] = int(counts.get(platform_id) or 0) + 1
        row.platform_counts = counts
        row.last_seen_at = now
        # Keep first-seen query_text; refresh topic_id if parent moved (rare).
        row.topic_id = topic_id
        # Do not revive dismissed/promoted.
        upserted += 1
    return upserted


def upsert_prompt_fanouts_for_response(
    db: Session,
    *,
    prompt_id: UUID,
    platform: str,
    queries: list[str] | tuple[str, ...],
    seen_at: datetime | None = None,
) -> int:
    """Load parent prompt; skip fanout children; upsert candidates."""
    prompt = db.get(Prompt, prompt_id)
    if prompt is None or prompt.deleted:
        return 0
    if str(prompt.kind or PROMPT_KIND_ROOT) == PROMPT_KIND_FANOUT:
        return 0
    return upsert_prompt_fanouts(
        db,
        subject_id=prompt.subject_id,
        parent_prompt_id=prompt.id,
        topic_id=prompt.topic_id,
        platform=platform,
        queries=queries,
        seen_at=seen_at,
    )


def mark_prompt_fanout_promoted(
    db: Session,
    *,
    subject_id: UUID,
    parent_prompt_id: UUID,
    query: str,
    promoted_prompt_id: UUID,
) -> SubjectPromptFanout | None:
    key = normalize_fanout_query_key(query)
    if not key:
        return None
    row = db.execute(
        select(SubjectPromptFanout).where(
            SubjectPromptFanout.subject_id == subject_id,
            SubjectPromptFanout.parent_prompt_id == parent_prompt_id,
            SubjectPromptFanout.query_key == key,
            SubjectPromptFanout.deleted.is_(False),
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    row.status = FANOUT_STATUS_PROMOTED
    row.promoted_prompt_id = promoted_prompt_id
    return row


def dismiss_prompt_fanout(
    db: Session,
    *,
    subject_id: UUID,
    fanout_id: UUID,
) -> SubjectPromptFanout:
    row = db.get(SubjectPromptFanout, fanout_id)
    if row is None or row.deleted or row.subject_id != subject_id:
        raise ValueError("扇出候选不存在")
    if row.status == FANOUT_STATUS_PROMOTED:
        raise ValueError("已升级的候选不能忽略")
    row.status = FANOUT_STATUS_DISMISSED
    db.commit()
    db.refresh(row)
    return row
