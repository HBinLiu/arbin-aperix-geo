"""Analysis response list — shared by sentiment page and prompt detail."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseSignal, Prompt, Subject
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._sql_scope import scope_filters
from aperix_geo.services.analysis.aggregate import mentioned_brands_for_response
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.signal_load import (
    LLMResponseSignalRow,
    load_llm_response_other_brand_signals,
    load_llm_response_signals,
)
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.sentiment import api_sentiment_label, api_sentiment_score
from aperix_geo.utils.text import reply_text, truncate_text

AnalysisResponseSortField = Literal["created_at", "sentiment_score", "rank"]
_MAX_PAGE_SIZE = 100


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
    return safe_page, safe_page_size


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


def _paginate(items: list[Any], *, page: int, page_size: int) -> tuple[list[Any], int]:
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return items[start : start + safe_page_size], total


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
    filters = [
        *scope_filters(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
        ),
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


def _sort_prompt_chat_responses(
    responses: list[Any],
    *,
    signal_by_response: dict[UUID, LLMResponseSignalRow],
    sort_by: AnalysisResponseSortField,
    order: str,
) -> list[Any]:
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


def _response_row_from_signal(
    *,
    response_id: UUID,
    platform_id: str,
    prompt_id: UUID,
    prompt_text: str,
    reply_preview: str,
    created_at: datetime,
    signal: LLMResponseSignalRow | None,
    all_signals: list[LLMResponseSignalRow],
    entities: list,
) -> dict[str, Any]:
    mentioned = signal.mentioned if signal is not None else False
    rank = (
        round(float(signal.mention_rank), 1)
        if signal is not None and has_mention_rank(signal.mention_rank)
        else None
    )
    cited = signal.cited_on_source if signal is not None else False
    score = signal.sentiment_score if signal is not None else 0.0
    return {
        "response_id": str(response_id),
        "platform_id": platform_id,
        "prompt_id": str(prompt_id),
        "prompt_text": prompt_text,
        "sentiment_score": api_sentiment_score(score),
        "sentiment_label": api_sentiment_label(score),
        "sentiment_reason": (signal.sentiment_reason or None) if signal else None,
        "reply_preview": reply_preview,
        "created_at": created_at.isoformat(),
        "mentioned": mentioned,
        "rank": rank,
        "mentioned_brands": mentioned_brands_for_response(
            response_id,
            all_signals=all_signals,
            entities=entities,
        ),
        "cited_on_source": cited,
    }


def _prompt_chat_response_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID,
    focus_signals: list[LLMResponseSignalRow],
    all_signals: list[LLMResponseSignalRow],
    entities: list,
    sort_by: AnalysisResponseSortField,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    """提示词详情 · 聊天 Tab：该提示词下全部回复（含未提及）。"""
    prompt = db.get(Prompt, prompt_id)
    prompt_text = prompt.text if prompt else ""
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
    page_rows, total = _paginate(ordered, page=page, page_size=page_size)
    rows: list[dict[str, Any]] = []
    for response in page_rows:
        signal = signal_by_response.get(response.id)
        rows.append(
            _response_row_from_signal(
                response_id=response.id,
                platform_id=response.platform,
                prompt_id=prompt_id,
                prompt_text=prompt_text,
                reply_preview=truncate_text(reply_text(response.raw_text), 120, suffix="…"),
                created_at=response.created_at,
                signal=signal,
                all_signals=all_signals,
                entities=entities,
            )
        )
    return rows, total


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

    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    offset = (safe_page - 1) * safe_page_size
    page_stmt = _order_mentioned_signal_stmt(base, sort_by=sort_by, order=order).limit(safe_page_size).offset(offset)
    page_rows = db.execute(page_stmt).all()
    if not page_rows:
        return [], total

    response_ids = {row.response_id for row in page_rows}
    mention_brand_signals = [
        *load_llm_response_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            response_ids=list(response_ids),
        ),
        *load_llm_response_other_brand_signals(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            response_ids=list(response_ids),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for row in page_rows:
        prompt = prompts.get(row.prompt_id)
        rank = (
            round(float(row.mention_rank), 1)
            if has_mention_rank(row.mention_rank)
            else None
        )
        score = float(row.sentiment_score or 0)
        rows.append(
            {
                "response_id": str(row.response_id),
                "platform_id": str(row.platform),
                "prompt_id": str(row.prompt_id),
                "prompt_text": prompt.text if prompt else "",
                "sentiment_score": api_sentiment_score(score),
                "sentiment_label": api_sentiment_label(score),
                "sentiment_reason": str(row.sentiment_reason or "") or None,
                "reply_preview": truncate_text(reply_text(row.raw_text), 120, suffix="…"),
                "created_at": row.created_at.isoformat(),
                "mentioned": True,
                "rank": rank,
                "mentioned_brands": mentioned_brands_for_response(
                    row.response_id,
                    all_signals=mention_brand_signals,
                    entities=entities,
                ),
                "cited_on_source": bool(row.cited_on_source),
            }
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
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    resolved_sort = _resolve_sort_field(sort_by)
    focus_entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)

    if prompt_id is not None and sentiment_label is None:
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
        focus_signals = [row for row in signals if row.entity_id == focus_entity.id]
        items, total = _prompt_chat_response_page(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            focus_signals=focus_signals,
            all_signals=mention_brand_signals,
            entities=entities,
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
