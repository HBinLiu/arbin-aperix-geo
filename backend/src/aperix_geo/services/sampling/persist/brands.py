"""Map entity signal drafts to brand sync inputs and upsert tb_brands."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, Subject
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.services.brand.sync import sync_brands_for_entities
from aperix_geo.services.brand.types import BrandSyncEntity
from aperix_geo.services.sampling.mentions import competitor_by_id
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def brand_sync_entity_for_draft(subject: Subject, draft: EntitySignalDraft) -> BrandSyncEntity:
    if draft.entity_kind == "own":
        own = own_entity(subject)
        display = (subject.brand or own.label).strip() or own.label
        return BrandSyncEntity(
            entity_id=draft.entity_id,
            entity_kind="own",
            entity_label=draft.entity_label,
            brand=display,
            domain=subject.domain or "",
            website_url=subject.website_url or "",
            aliases=tuple(str(x) for x in (subject.aliases or []) if str(x).strip()),
        )

    if draft.entity_kind == "competitor":
        competitor = competitor_by_id(subject).get(UUID(draft.entity_id))
        if competitor is None:
            return BrandSyncEntity(
                entity_id=draft.entity_id,
                entity_kind="competitor",
                entity_label=draft.entity_label,
                brand=draft.entity_label,
            )
        return BrandSyncEntity(
            entity_id=draft.entity_id,
            entity_kind="competitor",
            entity_label=draft.entity_label,
            brand=(competitor.brand or draft.entity_label).strip(),
            domain=competitor.domain or "",
            website_url=competitor.website_url or "",
            aliases=tuple(str(x) for x in (competitor.aliases or []) if str(x).strip()),
            summary=(competitor.summary or "").strip(),
        )

    return BrandSyncEntity(
        entity_id=draft.entity_id,
        entity_kind="other",
        entity_label=draft.entity_label,
    )


def sync_brands_for_drafts(
    db: Session,
    *,
    subject: Subject,
    drafts: list[EntitySignalDraft],
    raw_text: str = "",
    urls: list[str] | None = None,
    allow_search: bool = False,
) -> dict[str, Brand]:
    entities = [brand_sync_entity_for_draft(subject, draft) for draft in drafts]
    return sync_brands_for_entities(
        db,
        subject_id=subject.id,
        entities=entities,
        raw_text=raw_text,
        urls=urls,
        allow_search=allow_search,
    )
