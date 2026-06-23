"""Load persisted signals and merge with document-layer parsed JSON."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseSignal, Subject
from aperix_geo.services.analysis.entity import list_analysis_entities
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.signal_draft import drafts_to_records
from aperix_geo.services.sampling.signals.match import match_terms_for_entity_signal
from aperix_geo.utils.net import brand_from
from aperix_geo.utils.mention import api_mention_rank
from aperix_geo.utils.sentiment import (
    api_sentiment_label,
    api_sentiment_score,
)


def _api_primary_domain(value: str) -> str:
    return brand_from(value)


def _signal_record(
    *,
    subject: Subject,
    entity_id: str,
    entity_kind: str,
    entity_label: str,
    primary_domain: str,
    **fields: object,
) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "entity_label": entity_label,
        "primary_domain": primary_domain,
        "match_terms": match_terms_for_entity_signal(
            subject,
            entity_id=entity_id,
            entity_kind=entity_kind,
            entity_label=entity_label,
            primary_domain=primary_domain,
        ),
        **fields,
    }


def entity_signal_records_for_response(
    db: Session,
    *,
    response_id,
    subject: Subject,
) -> list[dict[str, object]]:
    """Load persisted signals and attach entity_label for API / UI consumers."""
    label_by_id = {entity.id: entity.label for entity in list_analysis_entities(subject)}
    rows = db.execute(
        select(LLMResponseSignal)
        .where(LLMResponseSignal.response_id == response_id)
        .order_by(LLMResponseSignal.entity_kind, LLMResponseSignal.entity_id)
    ).scalars().all()
    records: list[dict[str, object]] = []
    for row in rows:
        entity_label = row.entity_label or label_by_id.get(row.entity_id, row.entity_id)
        records.append(
            _signal_record(
                subject=subject,
                entity_id=row.entity_id,
                entity_kind=row.entity_kind,
                entity_label=entity_label,
                primary_domain=_api_primary_domain(row.primary_domain),
                brand_id=str(row.brand_id),
                mentioned=row.mentioned,
                mention_count=row.mention_count,
                mention_rank=api_mention_rank(row.mention_rank),
                sentiment_score=api_sentiment_score(row.sentiment_score),
                sentiment_reason=row.sentiment_reason or None,
                sentiment_label=api_sentiment_label(row.sentiment_score),
                has_domain_link=row.has_domain_link,
                cited_on_source=row.cited_on_source,
                source_page_mentions_brand=row.cited_on_source,
            )
        )
    return records


def parsed_api_dict(
    db: Session,
    *,
    row: LLMResponse,
    subject: Subject,
    parsed: ParsedSamplingResult | None = None,
) -> dict[str, object]:
    """Merge document-layer parsed JSON with signals from tb_llm_response_signals."""
    document = parsed.to_dict() if parsed is not None else dict(row.parsed or {})
    signals = entity_signal_records_for_response(db, response_id=row.id, subject=subject)
    if not signals and parsed is not None and parsed.entity_signals:
        signals = []
        for draft_record in drafts_to_records(parsed.entity_signals):
            entity_label = str(draft_record.get("entity_label") or "")
            signals.append(
                _signal_record(
                    subject=subject,
                    entity_id=str(draft_record.get("entity_id") or ""),
                    entity_kind=str(draft_record.get("entity_kind") or ""),
                    entity_label=entity_label,
                    primary_domain=_api_primary_domain(str(draft_record.get("primary_domain") or "")),
                    brand_id=draft_record.get("brand_id"),
                    mentioned=draft_record.get("mentioned"),
                    mention_count=draft_record.get("mention_count"),
                    mention_rank=api_mention_rank(draft_record.get("mention_rank")),
                    sentiment_score=api_sentiment_score(draft_record.get("sentiment_score")),
                    sentiment_reason=draft_record.get("sentiment_reason") or None,
                    sentiment_label=api_sentiment_label(draft_record.get("sentiment_score")),
                    has_domain_link=draft_record.get("has_domain_link"),
                    cited_on_source=draft_record.get("cited_on_source"),
                    source_page_mentions_brand=draft_record.get("cited_on_source"),
                )
            )
    document["entity_signals"] = signals
    return document
