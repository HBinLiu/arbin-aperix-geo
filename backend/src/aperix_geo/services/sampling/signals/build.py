"""Map entity signal drafts to ORM rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from aperix_geo.db.models import Brand, EntityKind, LLMResponseSignal
from aperix_geo.services.brand.resolve import primary_domain_for_brand
from aperix_geo.utils.mention import persist_mention_rank
from aperix_geo.utils.sentiment import persist_sentiment_reason, persist_sentiment_score
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def _entity_kind_value(kind: str) -> str:
    if kind == EntityKind.own.value:
        return EntityKind.own.value
    if kind == EntityKind.competitor.value:
        return EntityKind.competitor.value
    return EntityKind.other.value


def draft_to_model_fields(draft: EntitySignalDraft) -> dict[str, object]:
    return {
        "mentioned": draft.mentioned,
        "mention_count": draft.mention_count,
        "mention_rank": persist_mention_rank(draft.mention_rank),
        "sentiment_score": persist_sentiment_score(draft.sentiment_score if draft.mentioned else None),
        "sentiment_reason": persist_sentiment_reason(draft.sentiment_reason if draft.mentioned else None),
        "has_domain_link": draft.has_domain_link,
        "cited_on_source": draft.cited_on_source,
    }


def build_llm_response_signal_rows(
    *,
    response_id: UUID,
    subject_id: UUID,
    prompt_id: UUID,
    platform: str,
    created_at: datetime,
    entity_signals: list[EntitySignalDraft],
    brands_by_entity_id: dict[str, Brand] | None = None,
) -> list[LLMResponseSignal]:
    brands_by_entity_id = brands_by_entity_id or {}
    rows: list[LLMResponseSignal] = []
    for draft in entity_signals:
        brand = brands_by_entity_id.get(draft.entity_id)
        if brand is None:
            raise ValueError(f"missing brand sync for entity_id={draft.entity_id!r}")
        primary_domain = primary_domain_for_brand(brand)
        rows.append(
            LLMResponseSignal(
                response_id=response_id,
                subject_id=subject_id,
                prompt_id=prompt_id,
                platform=platform,
                entity_id=draft.entity_id,
                entity_kind=_entity_kind_value(draft.entity_kind),
                brand_id=brand.id,
                entity_label=draft.entity_label,
                primary_domain=primary_domain,
                created_at=created_at,
                **draft_to_model_fields(draft),
            )
        )
    return rows
