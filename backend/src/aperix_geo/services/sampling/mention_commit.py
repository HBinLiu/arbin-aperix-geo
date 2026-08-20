"""Validated open-mention commit gate (offset + entity type + span quality)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from aperix_geo.services.brand.domain import other_entity_id
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.services.sampling.enumeration import extract_enumerated_spans, normalize_mention_span
from aperix_geo.services.sampling.mention_entities import (
    DEFAULT_ENTITY_TYPE,
    MentionEntityInput,
    MentionSource,
    ValidatedMention,
    locate_span,
    parse_span_offsets,
    validate_mention_entity,
)

MentionStatus = Literal["committed", "pending", "dismissed"]

_STATUS_PRIORITY = {"committed": 3, "pending": 2, "dismissed": 1}
_SOURCE_PRIORITY = {"absa": 2, "enum": 1}

__all__ = [
    "MentionCommitEvent",
    "MentionCommitPlan",
    "MentionEntityInput",
    "ValidatedMention",
    "build_mention_commit_plan",
    "locate_span",
    "validate_mention_entity",
]


@dataclass(frozen=True)
class MentionCommitEvent:
    text: str
    entity_type: str
    start: int
    end: int
    source: MentionSource
    status: MentionStatus
    entity_id: str
    mention_key: str
    absa_mentioned: bool | None = None
    sentiment_score: float | None = None
    sentiment_reason: str | None = None
    evidence_snippet: str = ""


@dataclass
class MentionCommitPlan:
    events: list[MentionCommitEvent] = field(default_factory=list)

    def committed(self) -> list[MentionCommitEvent]:
        return [event for event in self.events if event.status == "committed"]

    def pending(self) -> list[MentionCommitEvent]:
        return [event for event in self.events if event.status == "pending"]

    def to_dicts(self) -> list[dict[str, Any]]:
        return [asdict(event) for event in self.events]


def _absa_mentioned(entry: Any) -> bool | None:
    if not isinstance(entry, dict) or "mentioned" not in entry:
        return None
    return bool(entry.get("mentioned"))


def _absa_sentiment(entry: dict[str, Any]) -> tuple[float | None, str | None]:
    if entry.get("mentioned") is False:
        return None, None
    score_raw = entry.get("score")
    try:
        score = float(score_raw) if score_raw is not None else None
    except (TypeError, ValueError):
        score = None
    reason = str(entry.get("evidence") or "").strip() or None
    return score, reason


def _index_absa_others(others: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map normalize_brand_key → ABSA entry (first wins; prefer mentioned=true on collision)."""
    by_key: dict[str, dict[str, Any]] = {}
    for name, entry in others.items():
        if not isinstance(entry, dict):
            continue
        label = normalize_mention_span(str(name or ""))
        key = normalize_brand_key(label)
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = entry
            continue
        if not existing.get("mentioned") and entry.get("mentioned"):
            by_key[key] = entry
    return by_key


def _prefer_event(candidate: MentionCommitEvent, existing: MentionCommitEvent) -> bool:
    if _STATUS_PRIORITY[candidate.status] != _STATUS_PRIORITY[existing.status]:
        return _STATUS_PRIORITY[candidate.status] > _STATUS_PRIORITY[existing.status]
    return _SOURCE_PRIORITY.get(candidate.source, 0) > _SOURCE_PRIORITY.get(existing.source, 0)


def build_mention_commit_plan(
    raw_text: str,
    response_absa: dict[str, Any],
    *,
    excluded_keys: set[str],
) -> MentionCommitPlan:
    """Commit open-set mentions when ABSA confirms, or when enum
    already validated an in-text commercial span (ABSA may still dismiss)."""
    text = raw_text or ""
    others_raw = response_absa.get("other_brands_sentiment_absa")
    others = others_raw if isinstance(others_raw, dict) else {}
    absa_by_key = _index_absa_others(others)
    by_key: dict[str, MentionCommitEvent] = {}

    def upsert(validated: ValidatedMention, absa_entry: dict[str, Any] | None) -> None:
        key = normalize_brand_key(validated.text)
        if not key or key in excluded_keys:
            return
        absa_flag = _absa_mentioned(absa_entry) if absa_entry is not None else None
        if absa_flag is False:
            status: MentionStatus = "dismissed"
        elif absa_flag is True:
            status = "committed"
        elif validated.source == "enum":
            # High-precision recall: span already validated against raw text.
            status = "committed"
        else:
            status = "pending"
        score, reason = _absa_sentiment(absa_entry) if isinstance(absa_entry, dict) else (None, None)
        event = MentionCommitEvent(
            text=validated.text,
            entity_type=validated.entity_type,
            start=validated.start,
            end=validated.end,
            source=validated.source,
            status=status,
            entity_id=other_entity_id(validated.text),
            mention_key=key,
            absa_mentioned=absa_flag,
            sentiment_score=score,
            sentiment_reason=reason,
            evidence_snippet=text[validated.start : validated.end],
        )
        existing = by_key.get(key)
        if existing is None or _prefer_event(event, existing):
            by_key[key] = event

    for label in extract_enumerated_spans(text):
        key = normalize_brand_key(label)
        if not key or key in excluded_keys:
            continue
        validated = validate_mention_entity(
            text,
            MentionEntityInput(text=label, entity_type=DEFAULT_ENTITY_TYPE, source="enum"),
        )
        if validated is None:
            continue
        upsert(validated, absa_by_key.get(normalize_brand_key(validated.text)))

    for name, entry in others.items():
        if not isinstance(entry, dict):
            continue
        label = normalize_mention_span(str(name or ""))
        key = normalize_brand_key(label)
        if not label or not key or key in excluded_keys:
            continue
        start, end = parse_span_offsets(entry.get("start"), entry.get("end"))
        validated = validate_mention_entity(
            text,
            MentionEntityInput(
                text=label,
                entity_type=str(entry.get("entity_type") or entry.get("type") or DEFAULT_ENTITY_TYPE),
                start=start,
                end=end,
                source="absa",
            ),
        )
        if validated is None:
            continue
        upsert(validated, entry)

    return MentionCommitPlan(events=list(by_key.values()))
