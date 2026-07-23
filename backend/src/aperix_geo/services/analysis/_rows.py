"""Response list row builders for analysis pages."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from aperix_geo.services.analysis.aggregate import mentioned_brands_for_response
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.sentiment import api_sentiment_label, api_sentiment_score
from aperix_geo.utils.text import reply_text, truncate_text


def mention_rank_display(mention_rank: int | float | None) -> float | None:
    if not has_mention_rank(mention_rank):
        return None
    return round(float(mention_rank), 1)


def reply_preview(raw_text: str, *, limit: int = 120) -> str:
    return truncate_text(reply_text(raw_text), limit, suffix="…")


def build_citation_response_row(
    response: Any,
    signal: LLMResponseSignalRow | None,
    *,
    all_signals: list[LLMResponseSignalRow],
    entities: list,
) -> dict[str, Any] | None:
    if signal is None or not (signal.has_domain_link or signal.cited_on_source):
        return None
    from aperix_geo.services.sampling.fanout import (
        platform_exposes_search_queries,
        search_queries_from_parsed,
    )

    parsed = response.parsed if isinstance(getattr(response, "parsed", None), dict) else {}
    platform = str(response.platform or "")
    return {
        "response_id": str(response.id),
        "platform": platform,
        "reply_preview": reply_preview(response.raw_text),
        "mentioned_brands": mentioned_brands_for_response(
            response.id,
            all_signals=all_signals,
            entities=entities,
        ),
        "mentioned": signal.mentioned,
        "rank": mention_rank_display(signal.mention_rank),
        "created_at": response.created_at.isoformat(),
        "cited_on_source": signal.cited_on_source,
        "search_queries": search_queries_from_parsed(parsed),
        "fanout_supported": platform_exposes_search_queries(platform),
    }


def build_chat_response_row(
    *,
    response_id: UUID,
    platform_id: str,
    prompt_id: UUID,
    prompt_text: str,
    raw_text: str,
    created_at: datetime,
    signal: LLMResponseSignalRow | None,
    all_signals: list[LLMResponseSignalRow],
    entities: list,
    search_queries: list[str] | None = None,
) -> dict[str, Any]:
    from aperix_geo.services.sampling.fanout import platform_exposes_search_queries

    mentioned = signal.mentioned if signal is not None else False
    cited = signal.cited_on_source if signal is not None else False
    score = signal.sentiment_score if signal is not None else 0.0
    queries = [str(q).strip() for q in (search_queries or []) if str(q).strip()]
    return {
        "response_id": str(response_id),
        "platform_id": platform_id,
        "prompt_id": str(prompt_id),
        "prompt_text": prompt_text,
        "sentiment_score": api_sentiment_score(score),
        "sentiment_label": api_sentiment_label(score),
        "sentiment_reason": (signal.sentiment_reason or None) if signal else None,
        "reply_preview": reply_preview(raw_text),
        "created_at": created_at.isoformat(),
        "mentioned": mentioned,
        "rank": mention_rank_display(signal.mention_rank if signal else None),
        "mentioned_brands": mentioned_brands_for_response(
            response_id,
            all_signals=all_signals,
            entities=entities,
        ),
        "cited_on_source": cited,
        "search_queries": queries,
        "fanout_supported": platform_exposes_search_queries(platform_id),
    }


def build_sentiment_response_row(
    row: Any,
    *,
    prompt_text: str,
    all_signals: list[LLMResponseSignalRow],
    entities: list,
) -> dict[str, Any]:
    score = float(row.sentiment_score or 0)
    return {
        "response_id": str(row.response_id),
        "platform_id": str(row.platform),
        "prompt_id": str(row.prompt_id),
        "prompt_text": prompt_text,
        "sentiment_score": api_sentiment_score(score),
        "sentiment_label": api_sentiment_label(score),
        "sentiment_reason": str(row.sentiment_reason or "") or None,
        "reply_preview": reply_preview(row.raw_text),
        "created_at": row.created_at.isoformat(),
        "mentioned": True,
        "rank": mention_rank_display(row.mention_rank),
        "mentioned_brands": mentioned_brands_for_response(
            row.response_id,
            all_signals=all_signals,
            entities=entities,
        ),
        "cited_on_source": bool(row.cited_on_source),
    }
