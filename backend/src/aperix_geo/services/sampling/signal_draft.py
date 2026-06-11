"""Per-entity signal drafts built during sampling parse."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, competitor_entities, own_entity
from aperix_geo.services.sampling.mentions import (
    CompetitorEntry,
    competitor_entries,
    count_term,
    first_idx_any,
    host_mentions_domain,
    own_names,
)
from aperix_geo.utils.sentiment import sentiment_points


@dataclass
class EntitySignalDraft:
    entity_id: str
    entity_kind: str
    entity_label: str
    mentioned: bool = False
    mention_count: int = 0
    mention_rank: int | None = None
    rank_hint_first_index: int | None = None
    sentiment_score: float | None = None
    sentiment_label: str = "neutral"
    sentiment_reason: str | None = None
    has_domain_link: bool = False
    cited_on_source: bool = False


def init_entity_signal_drafts(subject: Subject) -> list[EntitySignalDraft]:
    own = own_entity(subject)
    drafts = [
        EntitySignalDraft(
            entity_id=OWN_ENTITY_ID,
            entity_kind="own",
            entity_label=own.label,
        )
    ]
    for entity in competitor_entities(subject):
        drafts.append(
            EntitySignalDraft(
                entity_id=entity.id,
                entity_kind="competitor",
                entity_label=entity.label,
            )
        )
    return drafts


def _draft_by_entity_label(drafts: list[EntitySignalDraft]) -> dict[str, EntitySignalDraft]:
    return {draft.entity_label: draft for draft in drafts}


def _apply_competitor_text_mentions(
    by_entity_label: dict[str, EntitySignalDraft],
    text: str,
    url_hosts: list[str],
    competitors: list[CompetitorEntry],
) -> None:
    for entry in competitors:
        draft = by_entity_label.get(entry.label)
        if draft is None:
            continue
        count = sum(count_term(text, term) for term in entry.terms if term)
        host_hit = host_mentions_domain(entry.domain, url_hosts)
        if count == 0 and host_hit:
            count = 1
        draft.mentioned = count > 0 or host_hit
        draft.mention_count = count
        draft.rank_hint_first_index = first_idx_any(text, entry.terms)


def apply_text_mentions(
    drafts: list[EntitySignalDraft],
    text: str,
    *,
    subject: Subject,
    url_hosts: list[str],
) -> list[CompetitorEntry]:
    names = own_names(subject)
    competitors = competitor_entries(subject)
    by_entity_label = _draft_by_entity_label(drafts)
    own_draft = by_entity_label[own_entity(subject).label]
    mention_count_own = sum(count_term(text, name) for name in names if name)
    own_draft.mentioned = mention_count_own > 0
    own_draft.mention_count = mention_count_own
    own_draft.rank_hint_first_index = first_idx_any(text, names)

    _apply_competitor_text_mentions(by_entity_label, text, url_hosts, competitors)

    compute_mention_ranks(drafts)
    return competitors


def compute_mention_ranks(drafts: list[EntitySignalDraft]) -> None:
    ranked: list[tuple[str, int]] = []
    for draft in drafts:
        if draft.rank_hint_first_index is None:
            continue
        ranked.append((draft.entity_label, draft.rank_hint_first_index))
    ranked.sort(key=lambda item: item[1])
    rank_by_entity_label = {label: index for index, (label, _) in enumerate(ranked, start=1)}
    for draft in drafts:
        draft.mention_rank = rank_by_entity_label.get(draft.entity_label)


def normalize_draft_metrics(draft: EntitySignalDraft) -> None:
    """Ensure mention_count is consistent with mentioned before persist."""
    if draft.mentioned and draft.mention_count == 0:
        draft.mention_count = 1


def build_mention_entity_signals(
    text: str,
    *,
    subject: Subject,
    url_hosts: list[str],
) -> tuple[list[EntitySignalDraft], list[CompetitorEntry]]:
    drafts = init_entity_signal_drafts(subject)
    competitors = apply_text_mentions(drafts, text, subject=subject, url_hosts=url_hosts)
    return drafts, competitors


def draft_to_record(draft: EntitySignalDraft) -> dict[str, Any]:
    data = asdict(draft)
    data.pop("rank_hint_first_index", None)
    return data


def draft_from_record(data: dict[str, Any]) -> EntitySignalDraft:
    return EntitySignalDraft(
        entity_id=str(data.get("entity_id") or ""),
        entity_kind=str(data.get("entity_kind") or ""),
        entity_label=str(data.get("entity_label") or ""),
        mentioned=bool(data.get("mentioned")),
        mention_count=int(data.get("mention_count") or 0),
        mention_rank=data.get("mention_rank"),
        sentiment_score=sentiment_points(data.get("sentiment_score")),
        sentiment_label=str(data.get("sentiment_label") or "neutral"),
        sentiment_reason=data.get("sentiment_reason"),
        has_domain_link=bool(data.get("has_domain_link")),
        cited_on_source=bool(data.get("cited_on_source")),
    )


def drafts_to_records(drafts: list[EntitySignalDraft]) -> list[dict[str, Any]]:
    return [draft_to_record(draft) for draft in drafts]


def drafts_from_records(records: list[dict[str, Any]]) -> list[EntitySignalDraft]:
    return [draft_from_record(record) for record in records]


def own_draft(drafts: list[EntitySignalDraft]) -> EntitySignalDraft:
    return next(draft for draft in drafts if draft.entity_kind == "own")


def draft_for_entity_label(drafts: list[EntitySignalDraft], entity_label: str) -> EntitySignalDraft | None:
    return _draft_by_entity_label(drafts).get(entity_label)
