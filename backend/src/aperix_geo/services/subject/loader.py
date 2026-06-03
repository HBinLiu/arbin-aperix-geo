"""Load Subject rows with competitor relationships for sampling."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from aperix_geo.db.models import Subject


def load_subject_with_competitors(
    db: Session,
    subject_id: UUID,
    *,
    tenant_id: UUID | None = None,
) -> Subject | None:
    q = (
        select(Subject)
        .options(
            joinedload(Subject.competitor_domains),
            joinedload(Subject.competitor_brands),
        )
        .where(Subject.id == subject_id)
    )
    if tenant_id is not None:
        q = q.where(Subject.tenant_id == tenant_id)
    return db.execute(q).unique().scalar_one_or_none()


def competitor_lists(subject: Subject) -> tuple[list[str], list[str]]:
    return (
        [c.domain for c in subject.competitor_domains],
        [c.name for c in subject.competitor_brands],
    )
