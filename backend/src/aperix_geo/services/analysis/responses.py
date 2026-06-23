"""Analysis response list — shared by sentiment page and prompt detail."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseSignal, Prompt, Subject
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.analysis._rows import build_sentiment_response_row
from aperix_geo.services.analysis._sql_scope import scope_kwargs, scope_where
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.responses_sql import query_prompt_chat_page
from aperix_geo.services.analysis.signal_load import (
    LLMResponseSignalRow,
    load_mention_brand_signals,
)
from aperix_geo.utils.mention import has_mention_rank

AnalysisResponseSortField = Literal["created_at", "sentiment_score", "rank"]


def _resolve_sort_field(sort_by: str | None) -> AnalysisResponseSortField:
    if sort_by in ("created_at", "sentiment_score", "rank"):
        return sort_by  # type: ignore[return-value]
    return "created_at"


def _mention_rank_sort_key(
    signal: LLMResponseSignalRow | None,
    *,
    order: str,
    created_at_ts: float,
) -> tuple[int, float, float]:
    has = signal is not None and has_mention_rank(signal.mention_rank)
    if not has:
        return (1, 0.0, -created_at_ts)
    rank = float(signal.mention_rank)
    return (0, rank if order == "asc" else -rank, -created_at_ts)


def _sort_prompt_chat_responses(
    responses: list[Any],
    *,
    signal_by_response: dict[UUID, LLMResponseSignalRow],
    sort_by: AnalysisResponseSortField,
    order: str,
) -> list[Any]:
    """In-memory sort for test mem path only."""
    if sort_by == "sentiment_score":
        def score_key(response: Any) -> tuple[float, float]:
            signal = signal_by_response.get(response.id)
            score = signal.sentiment_score if signal is not None else 0.0
            return score, -response.created_at.timestamp()

        if order == "desc":
            return sorted(responses, key=score_key, reverse=True)
        return sorted(responses, key=lambda response: (-score_key(response)[0], -response.created_at.timestamp()))

    if sort_by == "rank":
        return sorted(
            responses,
            key=lambda response: _mention_rank_sort_key(
                signal_by_response.get(response.id),
                order=order,
                created_at_ts=response.created_at.timestamp(),
            ),
        )

    reverse = order != "asc"
    return sorted(responses, key=lambda response: response.created_at, reverse=reverse)


def _sentiment_bucket_expr():
    return case(
        (LLMResponseSignal.sentiment_score <= 0, "negative"),
        (LLMResponseSignal.sentiment_score > 70, "positive"),
        (LLMResponseSignal.sentiment_score < 45, "negative"),
        else_="neutral",
    )


def _mentioned_signal_base_stmt(
    *,
    subject: Subject,
    entity_id: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID | None,
    sentiment_label: str | None,
) -> Select[tuple[Any, ...]]:
    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    filters = [
        *scope_where(**window),
        LLMResponseSignal.entity_id == entity_id,
        LLMResponseSignal.mentioned.is_(True),
    ]
    if sentiment_label:
        filters.append(_sentiment_bucket_expr() == sentiment_label)
    return (
        select(
            LLMResponseSignal.response_id.label("response_id"),
            LLMResponseSignal.prompt_id.label("prompt_id"),
            LLMResponseSignal.platform.label("platform"),
            LLMResponseSignal.mention_rank.label("mention_rank"),
            LLMResponseSignal.sentiment_score.label("sentiment_score"),
            LLMResponseSignal.sentiment_reason.label("sentiment_reason"),
            LLMResponseSignal.cited_on_source.label("cited_on_source"),
            LLMResponse.created_at.label("created_at"),
            LLMResponse.raw_text.label("raw_text"),
        )
        .join(LLMResponse, LLMResponseSignal.response_id == LLMResponse.id)
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*filters)
    )


def _order_mentioned_signal_stmt(
    stmt: Select[tuple[Any, ...]],
    *,
    sort_by: AnalysisResponseSortField,
    order: str,
) -> Select[tuple[Any, ...]]:
    if sort_by == "sentiment_score":
        column = LLMResponseSignal.sentiment_score
        return stmt.order_by(column.desc() if order == "desc" else column.asc(), LLMResponse.created_at.desc())
    if sort_by == "rank":
        rank_expr = case((LLMResponseSignal.mention_rank > 0, LLMResponseSignal.mention_rank), else_=None)
        if order == "asc":
            return stmt.order_by(rank_expr.asc().nulls_last(), LLMResponse.created_at.desc())
        return stmt.order_by(rank_expr.desc().nulls_last(), LLMResponse.created_at.desc())
    column = LLMResponse.created_at
    return stmt.order_by(column.desc() if order != "asc" else column.asc())


def _sentiment_response_page_sql(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID | None,
    prompts: dict[UUID, Any],
    entities: list,
    sentiment_label: str,
    sort_by: AnalysisResponseSortField,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    base = _mentioned_signal_base_stmt(
        subject=subject,
        entity_id=entity_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        sentiment_label=sentiment_label,
    )
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    if total == 0:
        return [], 0

    safe_page, safe_page_size = normalize_pagination(page, page_size)
    offset = (safe_page - 1) * safe_page_size
    page_stmt = _order_mentioned_signal_stmt(base, sort_by=sort_by, order=order).limit(safe_page_size).offset(offset)
    page_rows = db.execute(page_stmt).all()
    if not page_rows:
        return [], total

    response_ids = {row.response_id for row in page_rows}
    mention_brand_signals = load_mention_brand_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        response_ids=list(response_ids),
    )

    rows: list[dict[str, Any]] = []
    for row in page_rows:
        prompt = prompts.get(row.prompt_id)
        rows.append(
            build_sentiment_response_row(
                row,
                prompt_text=prompt.text if prompt else "",
                all_signals=mention_brand_signals,
                entities=entities,
            )
        )
    return rows, total


def build_analysis_responses(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
    sentiment_label: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str | None = None,
    order: str = "desc",
) -> dict[str, Any]:
    """回复明细：情感页按 sentiment_label 筛选；提示词详情传 prompt_id 且不设 label 时返回聊天列表。"""
    safe_page, safe_page_size = normalize_pagination(page, page_size)
    resolved_sort = _resolve_sort_field(sort_by)
    focus_entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)

    if prompt_id is not None and sentiment_label is None:
        prompt = db.get(Prompt, prompt_id)
        prompt_text = prompt.text if prompt else ""
        items, total = query_prompt_chat_page(
            db,
            subject=subject,
            entity_id=focus_entity.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            prompt_text=prompt_text,
            sort_by=resolved_sort,
            order=order,
            page=safe_page,
            page_size=safe_page_size,
        )
    elif sentiment_label is None:
        items, total = [], 0
    else:
        _topics, prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
        items, total = _sentiment_response_page_sql(
            db,
            subject=subject,
            entity_id=focus_entity.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            prompts=prompts,
            entities=entities,
            sentiment_label=sentiment_label,
            sort_by=resolved_sort,
            order=order,
            page=safe_page,
            page_size=safe_page_size,
        )

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }
