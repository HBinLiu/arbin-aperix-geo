"""Validated mention entity types and span validation (no commit / brand registry deps)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.services.sampling.enumeration import (
    is_plausible_commercial_span,
    normalize_mention_span,
)

COMMIT_ENTITY_TYPES = frozenset({"PRODUCT", "BRAND", "ORG", "SERVICE"})
DEFAULT_ENTITY_TYPE = "PRODUCT"
_CLAUSE_INSIDE = re.compile(r"[，,。；;：:！？?\n\r]")
MentionSource = Literal["absa", "enum", "discovery"]


@dataclass(frozen=True)
class MentionEntityInput:
    text: str
    entity_type: str = DEFAULT_ENTITY_TYPE
    start: int | None = None
    end: int | None = None
    source: MentionSource = "discovery"


@dataclass(frozen=True)
class ValidatedMention:
    text: str
    entity_type: str
    start: int
    end: int
    source: MentionSource


def normalize_entity_type(raw: Any) -> str:
    text = str(raw or DEFAULT_ENTITY_TYPE).strip().upper()
    return text if text in COMMIT_ENTITY_TYPES else DEFAULT_ENTITY_TYPE


def parse_span_offsets(raw_start: Any, raw_end: Any) -> tuple[int | None, int | None]:
    try:
        start = int(raw_start) if raw_start is not None else None
        end = int(raw_end) if raw_end is not None else None
    except (TypeError, ValueError):
        return None, None
    if start is None or end is None:
        return None, None
    return start, end


def locate_span(raw_text: str, span_text: str) -> tuple[int, int] | None:
    """Find the first substring occurrence that satisfies span boundary rules."""
    label = normalize_mention_span(span_text)
    if not label or not raw_text:
        return None
    flags = re.IGNORECASE if label.isascii() else 0
    for match in re.finditer(re.escape(label), raw_text, flags=flags):
        start, end = match.start(), match.end()
        if span_offsets_ok(raw_text, start, end, label):
            return start, end
    return None


def span_offsets_ok(raw_text: str, start: int, end: int, label: str) -> bool:
    if not (0 <= start < end <= len(raw_text)):
        return False
    slice_text = raw_text[start:end]
    if slice_text != label and slice_text.casefold() != label.casefold():
        return False
    if _CLAUSE_INSIDE.search(slice_text):
        return False
    return _boundaries_ok(raw_text, start, end, label)


def validate_mention_entity(raw_text: str, entity: MentionEntityInput) -> ValidatedMention | None:
    label = normalize_mention_span(entity.text)
    if not label or not is_plausible_commercial_span(label):
        return None
    entity_type = normalize_entity_type(entity.entity_type)

    start, end = entity.start, entity.end
    if start is not None and end is not None and span_offsets_ok(raw_text, start, end, label):
        pass
    else:
        located = locate_span(raw_text, label)
        if located is None:
            return None
        start, end = located

    return ValidatedMention(
        text=label,
        entity_type=entity_type,
        start=start,
        end=end,
        source=entity.source,
    )


def parse_discovery_entities(data: dict[str, Any], *, raw_text: str) -> list[ValidatedMention]:
    validated: list[ValidatedMention] = []
    seen: set[str] = set()

    def _append(entity: MentionEntityInput) -> None:
        ok = validate_mention_entity(raw_text, entity)
        if ok is None:
            return
        key = normalize_brand_key(ok.text)
        if not key or key in seen:
            return
        seen.add(key)
        validated.append(ok)

    entities_raw = data.get("entities")
    if isinstance(entities_raw, list):
        for item in entities_raw:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or item.get("span") or "").strip()
            if not text:
                continue
            start, end = parse_span_offsets(item.get("start"), item.get("end"))
            _append(
                MentionEntityInput(
                    text=text,
                    entity_type=str(item.get("type") or item.get("entity_type") or DEFAULT_ENTITY_TYPE),
                    start=start,
                    end=end,
                    source="discovery",
                )
            )
        return validated

    spans = data.get("mentioned_spans")
    if not isinstance(spans, list):
        return []
    for raw in spans:
        text = str(raw or "").strip()
        if text:
            _append(MentionEntityInput(text=text, source="discovery"))
    return validated


def _boundaries_ok(raw_text: str, start: int, end: int, label: str) -> bool:
    """ASCII word-boundary check; CJK relies on exact span + plausible filters."""
    if not label.isascii():
        return True
    before = raw_text[start - 1] if start > 0 else " "
    after = raw_text[end] if end < len(raw_text) else " "
    if before.isalnum() and label[0].isalnum():
        return False
    if after.isalnum() and label[-1].isalnum():
        return False
    return True
