"""Shared SQL aggregation expressions for analysis metrics."""

from __future__ import annotations

from sqlalchemy import and_, case, func

from aperix_geo.db.models import LLMResponseSignal


def mentioned_count_expr():
    return case((LLMResponseSignal.mentioned.is_(True), 1), else_=0)


def with_link_count_expr():
    return case(
        (
            and_(
                LLMResponseSignal.mentioned.is_(True),
                LLMResponseSignal.has_domain_link.is_(True),
            ),
            1,
        ),
        else_=0,
    )


def cited_on_source_count_expr():
    return case((LLMResponseSignal.cited_on_source.is_(True), 1), else_=0)


def agg_metric_columns():
    mentioned_expr = mentioned_count_expr()
    with_link_expr = with_link_count_expr()
    cited_expr = cited_on_source_count_expr()
    return (
        func.count(func.distinct(LLMResponseSignal.response_id)).label("response_count"),
        func.sum(mentioned_expr).label("mentioned_rows"),
        func.sum(LLMResponseSignal.mention_count).label("mention_total"),
        func.sum(with_link_expr).label("mention_with_link"),
        func.sum(cited_expr).label("cited_on_source_rows"),
        func.avg(LLMResponseSignal.mention_rank)
        .filter(LLMResponseSignal.mention_rank > 0)
        .label("avg_rank"),
        func.avg(LLMResponseSignal.sentiment_score)
        .filter(LLMResponseSignal.sentiment_score > 0)
        .label("sentiment_avg"),
    )
