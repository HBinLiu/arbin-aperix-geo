"""Reconcile historical signals when configured competitors are removed.

Entity id conventions:
- tb_brands open-set rows: entity_id="" (empty)
- tb_llm_response_signals open-set rows: entity_id="other:{label_hash}"
- configured own: entity_id="own"; competitor: entity_id=str(competitor.id)
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, Competitor, EntityKind, LLMResponseSignal, Subject
from aperix_geo.services.brand.domain import other_entity_id
from aperix_geo.services.brand.resolve import find_brand_by_entity_id
from aperix_geo.services.subject.labels import competitor_rank_label
from aperix_geo.utils.net import ensure_brand


def _brand_for_competitor(db: Session, *, subject_id: UUID, competitor: Competitor) -> Brand | None:
    return find_brand_by_entity_id(db, subject_id=subject_id, entity_id=str(competitor.id))


def realign_competitor_signal_entity_ids(db: Session, *, subject: Subject) -> int:
    """Point competitor signals at the current configured competitor IDs (repair stale entity_id)."""
    if not subject.competitors:
        return 0

    fixed = 0
    for competitor in subject.competitors:
        entity_id = str(competitor.id)
        brand = _brand_for_competitor(db, subject_id=subject.id, competitor=competitor)
        if brand is None:
            continue
        brand.entity_kind = EntityKind.competitor.value
        brand.entity_id = entity_id
        signals = list(
            db.execute(
                select(LLMResponseSignal).where(
                    LLMResponseSignal.subject_id == subject.id,
                    LLMResponseSignal.brand_id == brand.id,
                    LLMResponseSignal.entity_kind == EntityKind.competitor.value,
                    LLMResponseSignal.entity_id != entity_id,
                )
            )
            .scalars()
            .all()
        )
        label = competitor_rank_label(brand=competitor.brand or "", domain=competitor.domain or "")
        for signal in signals:
            signal.entity_id = entity_id
            signal.entity_label = label or signal.entity_label
            fixed += 1
    return fixed


def _demote_brand_to_open_set(brand: Brand) -> str:
    brand.entity_kind = EntityKind.other.value
    brand.entity_id = ""
    label = competitor_rank_label(brand=brand.brand or "", domain=brand.domain or "")
    if not label:
        label = ensure_brand(brand.brand, domain=brand.domain)
    return label or brand.brand or brand.domain or "unknown"


def demote_competitor_signals(
    db: Session,
    *,
    subject_id: UUID,
    competitor_id: UUID,
) -> int:
    """Revert competitor signals to open-set rows after a configured competitor is removed."""
    entity_id = str(competitor_id)
    brand_labels: dict[UUID, str] = {}

    canonical = find_brand_by_entity_id(db, subject_id=subject_id, entity_id=entity_id)
    if canonical is not None:
        brand_labels[canonical.id] = _demote_brand_to_open_set(canonical)

    signals = list(
        db.execute(
            select(LLMResponseSignal).where(
                LLMResponseSignal.subject_id == subject_id,
                LLMResponseSignal.entity_id == entity_id,
                LLMResponseSignal.entity_kind == EntityKind.competitor.value,
            )
        )
        .scalars()
        .all()
    )

    brand_ids = {row.brand_id for row in signals if row.brand_id is not None}
    for brand_id in brand_ids:
        if brand_id in brand_labels:
            continue
        brand = db.get(Brand, brand_id)
        if brand is None:
            continue
        brand_labels[brand_id] = _demote_brand_to_open_set(brand)

    demoted = 0
    for signal in signals:
        label = brand_labels.get(signal.brand_id) or signal.entity_label or "unknown"
        signal.entity_kind = EntityKind.other.value
        signal.entity_id = other_entity_id(label)
        signal.entity_label = label
        demoted += 1

    return demoted
