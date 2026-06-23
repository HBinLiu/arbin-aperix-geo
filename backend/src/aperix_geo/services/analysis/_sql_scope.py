"""Shared window filters for analysis SQL queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from aperix_geo.db.models import EntityKind, LLMResponseSignal, Prompt


def scope_filters(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID | None,
    brand_id: UUID | None = None,
) -> list[Any]:
    filters: list[Any] = [
        LLMResponseSignal.subject_id == subject_id,
        LLMResponseSignal.created_at >= dt_from,
        LLMResponseSignal.created_at <= dt_to,
        LLMResponseSignal.entity_kind.in_((EntityKind.own.value, EntityKind.competitor.value)),
    ]
    if platform:
        filters.append(LLMResponseSignal.platform.in_(platform))
    if topic_id:
        filters.append(Prompt.topic_id.in_(topic_id))
    if prompt_id is not None:
        filters.append(LLMResponseSignal.prompt_id == prompt_id)
    if brand_id is not None:
        filters.append(LLMResponseSignal.brand_id == brand_id)
    return filters


def scope_kwargs(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID | None,
    brand_id: UUID | None = None,
) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "dt_from": dt_from,
        "dt_to": dt_to,
        "platform": platform,
        "topic_id": topic_id,
        "prompt_id": prompt_id,
        "brand_id": brand_id,
    }


def scope_where(**window: Any) -> list[Any]:
    return scope_filters(
        subject_id=window["subject_id"],
        dt_from=window["dt_from"],
        dt_to=window["dt_to"],
        platform=window["platform"],
        topic_id=window["topic_id"],
        prompt_id=window["prompt_id"],
        brand_id=window.get("brand_id"),
    )
