"""Prompt detail response listings."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.utils.text import reply_text
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals


def build_prompt_detail_responses(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """提示词详情：聊天 / 引用率回复明细。"""
    entity = resolve_analysis_entity(subject, entity_id)
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    signal_by_response = {
        row.response_id: row for row in signals if row.entity_id == entity.id
    }

    chat: list[dict[str, Any]] = []
    citation: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: item.created_at, reverse=True):
        signal = signal_by_response.get(row.id)
        mentioned = signal.mentioned if signal is not None else False
        rank = (
            round(float(signal.mention_rank), 1)
            if signal is not None and signal.mention_rank is not None
            else None
        )
        cited = signal.cited_on_source if signal is not None else False
        item = {
            "response_id": str(row.id),
            "platform": row.platform,
            "reply_preview": reply_text(row.raw_text),
            "mentioned": mentioned,
            "rank": rank,
            "created_at": row.created_at.isoformat(),
            "cited_on_source": cited,
        }
        chat.append(item)
        if signal is not None and (signal.has_domain_link or signal.cited_on_source):
            citation.append(item)

    return {
        "entity_id": entity.id,
        "entity_label": entity.label,
        "chat_responses": chat,
        "citation_responses": citation,
    }
