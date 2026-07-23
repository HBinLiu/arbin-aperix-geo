"""SQL pagination for prompt chat response lists."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseSignal, Subject
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.analysis._query import response_ids_in_window_stmt
from aperix_geo.services.analysis._rows import build_chat_response_row
from aperix_geo.services.analysis.entity import list_analysis_entities
from aperix_geo.services.analysis.signal_load import load_mention_brand_signals

AnalysisResponseSortField = Literal["created_at", "sentiment_score", "rank"]


def _prompt_chat_base_stmt(
    *,
    subject_id: UUID,
    entity_id: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID,
) -> Select[tuple[Any, ...]]:
    window_ids = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    signal_join = and_(
        LLMResponseSignal.response_id == LLMResponse.id,
        LLMResponseSignal.entity_id == entity_id,
    )
    return (
        select(
            LLMResponse.id.label("response_id"),
            LLMResponse.platform.label("platform"),
            LLMResponse.prompt_id.label("prompt_id"),
            LLMResponse.created_at.label("created_at"),
            LLMResponse.raw_text.label("raw_text"),
            LLMResponse.parsed.label("parsed"),
            LLMResponseSignal.mention_rank.label("mention_rank"),
            LLMResponseSignal.sentiment_score.label("sentiment_score"),
            LLMResponseSignal.sentiment_reason.label("sentiment_reason"),
            LLMResponseSignal.cited_on_source.label("cited_on_source"),
            LLMResponseSignal.mentioned.label("mentioned"),
        )
        .select_from(LLMResponse)
        .outerjoin(LLMResponseSignal, signal_join)
        .where(LLMResponse.id.in_(window_ids))
    )


def _order_prompt_chat_stmt(
    stmt: Select[tuple[Any, ...]],
    *,
    sort_by: AnalysisResponseSortField,
    order: str,
) -> Select[tuple[Any, ...]]:
    if sort_by == "sentiment_score":
        score_expr = func.coalesce(LLMResponseSignal.sentiment_score, 0)
        return stmt.order_by(
            score_expr.desc() if order == "desc" else score_expr.asc(),
            LLMResponse.created_at.desc(),
        )
    if sort_by == "rank":
        rank_expr = case((LLMResponseSignal.mention_rank > 0, LLMResponseSignal.mention_rank), else_=None)
        if order == "asc":
            return stmt.order_by(rank_expr.asc().nulls_last(), LLMResponse.created_at.desc())
        return stmt.order_by(rank_expr.desc().nulls_last(), LLMResponse.created_at.desc())
    column = LLMResponse.created_at
    return stmt.order_by(column.desc() if order != "asc" else column.asc())


def _signal_from_chat_row(row: Any) -> Any | None:
    if row.mentioned is None and row.mention_rank is None and row.sentiment_score is None:
        return None
    return SimpleNamespace(
        mentioned=bool(row.mentioned),
        mention_rank=int(row.mention_rank or 0),
        sentiment_score=float(row.sentiment_score or 0),
        sentiment_reason=str(row.sentiment_reason or "") or None,
        cited_on_source=bool(row.cited_on_source),
    )


def _load_prompt_chat_page_sql(
    db: Session,
    *,
    subject: Subject,
    entity_id: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID,
    prompt_text: str,
    sort_by: AnalysisResponseSortField,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    base = _prompt_chat_base_stmt(
        subject_id=subject.id,
        entity_id=entity_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    if total == 0:
        return [], 0

    safe_page, safe_page_size = normalize_pagination(page, page_size)
    offset = (safe_page - 1) * safe_page_size
    page_stmt = _order_prompt_chat_stmt(base, sort_by=sort_by, order=order).limit(safe_page_size).offset(offset)
    page_rows = db.execute(page_stmt).all()
    if not page_rows:
        return [], total

    response_ids = [row.response_id for row in page_rows]
    mention_brand_signals = load_mention_brand_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        response_ids=response_ids,
    )
    entities = list_analysis_entities(subject)

    from aperix_geo.services.sampling.fanout import search_queries_from_parsed

    rows: list[dict[str, Any]] = []
    for row in page_rows:
        parsed = row.parsed if isinstance(row.parsed, dict) else {}
        rows.append(
            build_chat_response_row(
                response_id=row.response_id,
                platform_id=str(row.platform),
                prompt_id=prompt_id,
                prompt_text=prompt_text,
                raw_text=row.raw_text,
                created_at=row.created_at,
                signal=_signal_from_chat_row(row),
                all_signals=mention_brand_signals,
                entities=entities,
                search_queries=search_queries_from_parsed(parsed),
            )
        )
    return rows, total


class _QueryPromptChatPage:
    """Patchable prompt chat page query (tests assign to `.override`)."""

    override: Callable[..., tuple[list[dict[str, Any]], int]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        entity_id: str,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        prompt_id: UUID,
        prompt_text: str,
        sort_by: AnalysisResponseSortField = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                entity_id=entity_id,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
                prompt_id=prompt_id,
                prompt_text=prompt_text,
                sort_by=sort_by,
                order=order,
                page=page,
                page_size=page_size,
            )
        return _load_prompt_chat_page_sql(
            db,
            subject=subject,
            entity_id=entity_id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            prompt_id=prompt_id,
            prompt_text=prompt_text,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )


query_prompt_chat_page = _QueryPromptChatPage()
