"""In-memory prompt chat page query for unit tests."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._rows import build_chat_response_row
from aperix_geo.services.analysis.entity import list_analysis_entities
from aperix_geo.services.analysis.responses import (
    AnalysisResponseSortField,
    _mention_rank_sort_key,
    _sort_prompt_chat_responses,
)
from aperix_geo.services.analysis.signal_load import (
    LLMResponseSignalRow,
    load_llm_response_other_brand_signals,
    load_llm_response_signals,
)


def mem_prompt_chat_page(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    dt_from,
    dt_to,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID,
    prompt_text: str,
    sort_by: AnalysisResponseSortField = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    other_brand_signals = load_llm_response_other_brand_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    mention_brand_signals = [*signals, *other_brand_signals]
    focus_signals = [row for row in signals if row.entity_id == entity_id]
    entities = list_analysis_entities(subject)

    response_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    signal_by_response = {row.response_id: row for row in focus_signals}
    ordered = _sort_prompt_chat_responses(
        response_rows,
        signal_by_response=signal_by_response,
        sort_by=sort_by,
        order=order,
    )
    safe_page, safe_page_size = normalize_pagination(page, page_size)
    total = len(ordered)
    start = (safe_page - 1) * safe_page_size
    page_rows = ordered[start : start + safe_page_size]

    rows: list[dict[str, Any]] = []
    for response in page_rows:
        signal: LLMResponseSignalRow | None = signal_by_response.get(response.id)
        rows.append(
            build_chat_response_row(
                response_id=response.id,
                platform_id=response.platform,
                prompt_id=prompt_id,
                prompt_text=prompt_text,
                raw_text=response.raw_text,
                created_at=response.created_at,
                signal=signal,
                all_signals=mention_brand_signals,
                entities=entities,
            )
        )
    return rows, total
