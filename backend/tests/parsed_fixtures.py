"""Helpers for building flat entity_signals in test parsed payloads."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

COMPETITOR_ENTITY_ID = "comp-beta"


@dataclass
class _FakeBrand:
    id: uuid.UUID
    domain: str = ""


def brands_by_entity_id_for_drafts(drafts) -> dict[str, _FakeBrand]:
    brands: dict[str, _FakeBrand] = {}
    for draft in drafts:
        if draft.entity_id not in brands:
            brands[draft.entity_id] = _FakeBrand(id=uuid.uuid4(), domain=draft.entity_label)
    return brands


def entity_signal(**kwargs: Any) -> dict[str, Any]:
    record = {
        "entity_id": "own",
        "entity_kind": "own",
        "entity_label": "aperix.com",
        "mentioned": False,
        "mention_count": 0,
        "mention_rank": None,
        "sentiment_score": None,
        "has_domain_link": False,
        "cited_on_source": False,
    }
    record.update(kwargs)
    return record


def competitor_signal(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("entity_id", COMPETITOR_ENTITY_ID)
    kwargs.setdefault("entity_kind", "competitor")
    kwargs.setdefault("entity_label", "Beta")
    return entity_signal(**kwargs)


def parsed_payload(*signals: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"entity_signals": list(signals), **extra}


def signal_rows_from_payload(
    rows: list,
    subject,
    *,
    parsed_payloads: list[dict[str, Any]],
) -> list:
    """Build LLMResponseSignalRow list from test fixture parsed payloads."""
    from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
    from aperix_geo.services.sampling.signal_draft import drafts_from_records
    from aperix_geo.services.sampling.signals import build_llm_response_signal_rows

    out = []
    for response, payload in zip(rows, parsed_payloads, strict=True):
        drafts = drafts_from_records(list(payload.get("entity_signals") or []))
        if subject.competitors:
            comp_id = str(subject.competitors[0].id)
            for draft in drafts:
                if draft.entity_kind == "competitor":
                    draft.entity_id = comp_id
        for signal in build_llm_response_signal_rows(
            response_id=response.id,
            subject_id=subject.id,
            prompt_id=response.prompt_id,
            platform=response.platform,
            created_at=response.created_at,
            entity_signals=drafts,
            brands_by_entity_id=brands_by_entity_id_for_drafts(drafts),  # type: ignore[arg-type]
        ):
            out.append(LLMResponseSignalRow.from_model(signal))
    return out
