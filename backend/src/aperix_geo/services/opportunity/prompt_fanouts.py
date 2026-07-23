"""Opportunity list: materialized prompt fan-out candidates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, SubjectPromptFanout, Topic
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.prompts.persist import PromptValidationError, promote_fanout_prompt
from aperix_geo.services.sampling.prompt_fanouts import (
    FANOUT_STATUS_PENDING,
    dismiss_prompt_fanout,
)


def _filter_clauses(
    *,
    subject_id: UUID,
    status: str,
    topic_id: list[UUID] | None,
    search: str | None,
    dt_from: datetime | None,
    dt_to: datetime | None,
) -> list[Any]:
    clauses: list[Any] = [
        SubjectPromptFanout.subject_id == subject_id,
        SubjectPromptFanout.deleted.is_(False),
        SubjectPromptFanout.status == status,
    ]
    if topic_id:
        clauses.append(SubjectPromptFanout.topic_id.in_(topic_id))
    if search and search.strip():
        term = f"%{search.strip()}%"
        clauses.append(
            or_(
                SubjectPromptFanout.query_text.ilike(term),
                SubjectPromptFanout.query_key.ilike(term),
            )
        )
    if dt_from is not None:
        clauses.append(SubjectPromptFanout.last_seen_at >= dt_from)
    if dt_to is not None:
        clauses.append(SubjectPromptFanout.last_seen_at <= dt_to)
    return clauses


def build_prompt_fanouts_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    status: str = FANOUT_STATUS_PENDING,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    page, page_size = normalize_pagination(page, page_size)
    offset = (page - 1) * page_size
    clauses = _filter_clauses(
        subject_id=subject.id,
        status=status,
        topic_id=topic_id,
        search=search,
        dt_from=dt_from,
        dt_to=dt_to,
    )

    total = int(
        db.execute(select(func.count()).select_from(SubjectPromptFanout).where(*clauses)).scalar_one()
        or 0
    )
    freq_sum = int(
        db.execute(
            select(func.coalesce(func.sum(SubjectPromptFanout.frequency), 0)).where(*clauses)
        ).scalar_one()
        or 0
    )

    rows = list(
        db.execute(
            select(SubjectPromptFanout)
            .where(*clauses)
            .order_by(
                SubjectPromptFanout.frequency.desc(),
                SubjectPromptFanout.last_seen_at.desc(),
                SubjectPromptFanout.id.asc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    parent_ids = {row.parent_prompt_id for row in rows}
    topic_ids = {row.topic_id for row in rows}
    parents = {
        p.id: p
        for p in db.execute(select(Prompt).where(Prompt.id.in_(parent_ids))).scalars().all()
    } if parent_ids else {}
    topics = {
        t.id: t
        for t in db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
    } if topic_ids else {}

    items: list[dict[str, Any]] = []
    for row in rows:
        freq = int(row.frequency or 0)
        parent = parents.get(row.parent_prompt_id)
        topic = topics.get(row.topic_id)
        items.append(
            {
                "id": str(row.id),
                "query_text": row.query_text,
                "frequency": freq,
                "contribution_rate": round(freq / freq_sum, 4) if freq_sum else 0.0,
                "platform_counts": dict(row.platform_counts or {}),
                "parent_prompt_id": str(row.parent_prompt_id),
                "parent_prompt_text": (parent.text if parent else "") or "",
                "topic_id": str(row.topic_id),
                "topic_name": (topic.name if topic else "") or "",
                "status": row.status,
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else "",
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else "",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "frequency_total": freq_sum,
    }


def promote_opportunity_prompt_fanout(
    db: Session,
    *,
    subject_id: UUID,
    fanout_id: UUID,
    enabled: bool = False,
) -> dict[str, Any]:
    row = db.get(SubjectPromptFanout, fanout_id)
    if row is None or row.deleted or row.subject_id != subject_id:
        raise PromptValidationError("扇出候选不存在")
    if row.status != FANOUT_STATUS_PENDING:
        raise PromptValidationError("仅待处理候选可升级")

    prompt = promote_fanout_prompt(
        db,
        subject_id,
        parent_prompt_id=row.parent_prompt_id,
        query=row.query_text,
        enabled=enabled,
    )
    # promote_fanout_prompt commits and marks candidate; refresh
    db.refresh(row)
    return {
        "fanout_id": str(row.id),
        "prompt_id": str(prompt.id),
        "query_text": prompt.text,
        "status": row.status,
    }


def dismiss_opportunity_prompt_fanout(
    db: Session,
    *,
    subject_id: UUID,
    fanout_id: UUID,
) -> dict[str, Any]:
    try:
        row = dismiss_prompt_fanout(db, subject_id=subject_id, fanout_id=fanout_id)
    except ValueError as exc:
        raise PromptValidationError(str(exc)) from exc
    return {"id": str(row.id), "status": row.status}
