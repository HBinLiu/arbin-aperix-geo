"""SQL aggregation for open-set brand opportunity windows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Float, String, and_, case, func, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, EntityKind, LLMResponseSignal, Prompt, Subject, SubjectType
from aperix_geo.services.analysis._query import count_responses_in_window
from aperix_geo.services.analysis._sql_metrics import (
    cited_on_source_count_expr,
    with_link_count_expr,
)
from aperix_geo.services.analysis._sql_scope import scope_kwargs, scope_where
from aperix_geo.services.analysis.aggregate import metrics_to_dict
from aperix_geo.services.analysis.metrics import MetricsBundle
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.net import ensure_brand
from aperix_geo.utils.sentiment import api_sentiment_label


def _open_brand_signal_filters(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> list[Any]:
    filters: list[Any] = [
        LLMResponseSignal.subject_id == subject_id,
        LLMResponseSignal.created_at >= dt_from,
        LLMResponseSignal.created_at <= dt_to,
        LLMResponseSignal.entity_kind == EntityKind.other.value,
        LLMResponseSignal.brand_id.isnot(None),
    ]
    if platform:
        filters.append(LLMResponseSignal.platform.in_(platform))
    if topic_id:
        filters.append(Prompt.topic_id.in_(topic_id))
    return filters


def _open_brand_metrics_subquery(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
):
    filters = _open_brand_signal_filters(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    with_link_expr = with_link_count_expr()
    return (
        select(
            LLMResponseSignal.brand_id.label("brand_id"),
            func.count(func.distinct(LLMResponseSignal.response_id))
            .filter(LLMResponseSignal.mentioned.is_(True))
            .label("mentioned_responses"),
            func.sum(LLMResponseSignal.mention_count).label("mention_total"),
            func.sum(with_link_expr).label("mention_with_link"),
            func.sum(cited_on_source_count_expr()).label("cited_on_source_rows"),
            func.avg(LLMResponseSignal.mention_rank)
            .filter(LLMResponseSignal.mention_rank > 0)
            .label("avg_rank"),
            func.avg(LLMResponseSignal.sentiment_score)
            .filter(LLMResponseSignal.sentiment_score > 0)
            .label("sentiment_avg"),
        )
        .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
        .where(*filters)
        .group_by(LLMResponseSignal.brand_id)
    ).subquery()


def metrics_bundle_for_open_brand(
    row: Any,
    *,
    subject: Subject,
    total_voice: int,
    window_response_total: int,
) -> MetricsBundle:
    """Open-set brands only persist signal rows when mentioned — use window total as denominator."""
    if window_response_total <= 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_rate=None,
            share_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_label=None,
            citation_coverage=None,
        )

    mentioned = int(row.mentioned_responses or 0)
    mention_total = int(row.mention_total or 0)
    mention_with_link = int(row.mention_with_link or 0)
    cited_on_source_rows = int(row.cited_on_source_rows or 0)
    avg_rank_raw = row.avg_rank
    avg_rank = round(float(avg_rank_raw), 2) if avg_rank_raw is not None else None
    if avg_rank is not None and not has_mention_rank(avg_rank):
        avg_rank = None

    sentiment_avg_raw = row.sentiment_avg
    if sentiment_avg_raw is not None:
        avg_sentiment = round(float(sentiment_avg_raw), 1)
    else:
        avg_sentiment = 0.0

    return MetricsBundle(
        response_count=window_response_total,
        visibility_rate=round(mentioned / window_response_total, 4),
        mention_rate=round(mention_total / window_response_total, 4),
        share_voice=round(mention_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=avg_rank,
        citation_rate=round(mention_with_link / mentioned, 4) if mentioned > 0 else None,
        sentiment_score=avg_sentiment,
        sentiment_label=api_sentiment_label(avg_sentiment),
        citation_coverage=round(cited_on_source_rows / window_response_total, 4)
        if subject.type == SubjectType.domain or subject.website_url
        else None,
    )


def _search_pattern(needle: str) -> str:
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


_SORT_COLUMNS = {
    "visibility_rate": "visibility_rate",
    "mention_rate": "mention_rate",
    "share_voice": "share_voice",
    "average_rank": "avg_rank",
    "citation_rate": "citation_rate",
    "sentiment_score": "sentiment_avg",
    "brand": "brand_label",
}


def query_brands_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)

    window = scope_kwargs(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )
    window_response_total = count_responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    total_voice = int(
        db.scalar(
            select(func.coalesce(func.sum(LLMResponseSignal.mention_count), 0))
            .join(Prompt, LLMResponseSignal.prompt_id == Prompt.id)
            .where(*scope_where(**window))
        )
        or 0
    )

    agg = _open_brand_metrics_subquery(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    window_total = func.nullif(float(window_response_total), 0.0)
    mentioned_responses = agg.c.mentioned_responses
    mention_total = agg.c.mention_total
    mention_with_link = agg.c.mention_with_link

    visibility_rate = (mentioned_responses.cast(Float) / window_total).label("visibility_rate")
    mention_rate = (mention_total.cast(Float) / window_total).label("mention_rate")
    share_voice = case(
        (and_(mention_total > 0, total_voice > 0), mention_total.cast(Float) / float(total_voice)),
        else_=None,
    ).label("share_voice")
    citation_rate = case(
        (mentioned_responses > 0, mention_with_link.cast(Float) / mentioned_responses.cast(Float)),
        else_=None,
    ).label("citation_rate")
    brand_label = func.coalesce(
        func.nullif(Brand.brand, ""),
        func.nullif(Brand.domain, ""),
        agg.c.brand_id.cast(String),
    ).label("brand_label")

    base = (
        select(
            agg.c.brand_id,
            Brand.brand,
            Brand.domain,
            Brand.website_url,
            agg.c.mentioned_responses,
            agg.c.mention_total,
            agg.c.mention_with_link,
            agg.c.cited_on_source_rows,
            agg.c.avg_rank,
            agg.c.sentiment_avg,
            visibility_rate,
            mention_rate,
            share_voice,
            citation_rate,
            brand_label,
        )
        .join(Brand, Brand.id == agg.c.brand_id)
        .where(
            Brand.subject_id == subject.id,
            Brand.entity_kind == EntityKind.other.value,
            agg.c.mentioned_responses > 0,
        )
    ).subquery()

    filters: list[Any] = []
    search_text = (search or "").strip().lower()
    if search_text:
        pattern = _search_pattern(search_text)
        filters.append(
            or_(
                func.lower(base.c.brand).ilike(pattern),
                func.lower(base.c.domain).ilike(pattern),
            )
        )

    filtered = select(base).where(*filters).subquery() if filters else base

    sort_key = _SORT_COLUMNS.get(sort_by or "", "visibility_rate")
    sort_col = getattr(filtered.c, sort_key)
    order_clauses = [sort_col.desc().nullslast()] if order == "desc" else [sort_col.asc().nullsfirst()]
    order_clauses.append(filtered.c.brand_label.asc())

    offset = (safe_page - 1) * safe_page_size
    rows = db.execute(
        select(filtered, func.count().over().label("_total"))
        .order_by(*order_clauses)
        .offset(offset)
        .limit(safe_page_size)
    ).all()

    if not rows:
        total = int(db.scalar(select(func.count()).select_from(filtered)) or 0)
        return [], total

    total = int(rows[0]._total)
    items: list[dict[str, Any]] = []
    for row in rows:
        metrics = metrics_bundle_for_open_brand(
            row,
            subject=subject,
            total_voice=total_voice,
            window_response_total=window_response_total,
        )
        label = ensure_brand(str(row.brand or "").strip(), domain=str(row.domain or "").strip())
        domain = str(row.domain or "").strip()
        display_name = label or domain or str(row.brand_id)
        items.append(
            {
                "brand_id": str(row.brand_id),
                "label": label or domain or display_name,
                "display_name": display_name,
                "domain": domain,
                **metrics_to_dict(metrics),
            }
        )
    return items, total
