"""Prompt detail response listings."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._parsed import has_own_domain_link, mentions_own, reply_text
from aperix_geo.services.analysis._query import responses_in_window


def _subject_region(subject: Subject) -> str:
    scope = subject.monitoring_scope if isinstance(subject.monitoring_scope, dict) else {}
    region = str(scope.get("region") or "").strip()
    return region or "CN"


def _parse_rank(parsed: dict[str, Any]) -> float | None:
    rank = parsed.get("rank_own")
    if rank is None:
        return None
    try:
        return round(float(rank), 1)
    except (TypeError, ValueError):
        return None


def _has_citation_signal(parsed: dict[str, Any]) -> bool:
    urls_own = parsed.get("citation_urls_own") or []
    urls_all = parsed.get("citation_urls") or []
    return bool(
        urls_own
        or urls_all
        or has_own_domain_link(parsed)
        or parsed.get("cited_own_domain")
    )


def build_prompt_detail_responses(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """提示词详情：聊天 / 引用率回复明细。"""
    region = _subject_region(subject)
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )

    chat: list[dict[str, Any]] = []
    citation: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: item.created_at, reverse=True):
        parsed = row.parsed or {}
        item = {
            "response_id": str(row.id),
            "platform": row.platform,
            "reply_preview": reply_text(row.raw_text),
            "mentioned": mentions_own(parsed),
            "rank": _parse_rank(parsed),
            "region": region,
            "created_at": row.created_at.isoformat(),
            "cited_own_domain": bool(parsed.get("cited_own_domain")),
        }
        chat.append(item)
        if _has_citation_signal(parsed):
            citation.append(item)

    return {
        "region": region,
        "chat_responses": chat,
        "citation_responses": citation,
        "query_expansions": [],
    }
