"""Resolve analysis entity identifiers to canonical brand rows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponseSignal, Subject
from aperix_geo.services.analysis.entity import resolve_analysis_entity


def resolve_brand_id_for_analysis_entity(
    db: Session,
    *,
    subject: Subject,
    entity_id: str | None,
) -> UUID:
    """Map FilterBar entity_id (own / competitor UUID) to tb_brands.id."""
    from aperix_geo.services.brand.sync import sync_brand_for_entity
    from aperix_geo.services.sampling.persist.brands import brand_sync_entity_for_draft
    from aperix_geo.services.sampling.signal_draft import EntitySignalDraft

    entity = resolve_analysis_entity(subject, entity_id)
    existing = db.execute(
        select(LLMResponseSignal.brand_id)
        .where(
            LLMResponseSignal.subject_id == subject.id,
            LLMResponseSignal.entity_id == entity.id,
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    draft = EntitySignalDraft(
        entity_id=entity.id,
        entity_kind=entity.kind,
        entity_label=entity.label,
    )
    sync_entity = brand_sync_entity_for_draft(subject, draft)
    brand = sync_brand_for_entity(
        db,
        subject_id=subject.id,
        entity=sync_entity,
    )
    db.flush()
    return brand.id
