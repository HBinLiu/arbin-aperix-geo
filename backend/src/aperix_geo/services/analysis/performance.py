"""Topic, prompt, and platform performance tables."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis.aggregate import (
    group_signals_by_topic,
    metrics_from_signals,
)
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.signal_index import SignalWindowIndex
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals


def topics_performance_from_index(
    index: SignalWindowIndex,
    *,
    subject: Subject,
    entity_id: str,
    topics: dict[UUID, Topic],
    prompt_to_topic: dict[UUID, UUID],
) -> list[dict[str, Any]]:
    window_signals = [row for rows in index.by_date.values() for row in rows]
    by_topic_all = group_signals_by_topic(window_signals, prompt_to_topic=prompt_to_topic)
    entity_signals = index.by_entity.get(entity_id, [])
    grouped = group_signals_by_topic(entity_signals, prompt_to_topic=prompt_to_topic)
    out: list[dict[str, Any]] = []
    for tid, subset in grouped.items():
        topic = topics.get(tid)
        metrics = metrics_from_signals(
            subset,
            subject=subject,
            all_signals_for_voice=by_topic_all.get(tid, []),
        )
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": topic.name if topic else str(tid),
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "sentiment_label": metrics.sentiment_label,
                "response_count": metrics.response_count,
            }
        )
    return sorted(out, key=lambda x: x["topic_name"])


def topics_performance_from_signals(
    all_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
    topics: dict[UUID, Topic],
    prompts: dict[UUID, Prompt],
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis.signal_index import index_signals

    prompt_to_topic = {pid: p.topic_id for pid, p in prompts.items()}
    return topics_performance_from_index(
        index_signals(all_signals),
        subject=subject,
        entity_id=entity_id,
        topics=topics,
        prompt_to_topic=prompt_to_topic,
    )


def build_topics_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return []
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    topics, prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject_id)
    return topics_performance_from_signals(
        all_signals,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        prompts=prompts,
    )


_MAX_PROMPT_PAGE_SIZE = 100


def _normalize_prompt_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, _MAX_PROMPT_PAGE_SIZE))
    return safe_page, safe_page_size


def _apply_prompt_search(rows: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    query = (search or "").strip().casefold()
    if not query:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        prompt_text = str(row.get("prompt_text") or "").casefold()
        topic_name = str(row.get("topic_name") or "").casefold()
        if query in prompt_text or query in topic_name:
            out.append(row)
    return out


def _sort_prompt_metric_rows(
    rows: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if sort_by:
        reverse = order != "asc"
        if sort_by == "average_rank":
            reverse = order == "asc"

        def sort_key(row: dict[str, Any]) -> float:
            value = row.get(sort_by)
            if value is None:
                return float("inf") if sort_by == "average_rank" else (float("-inf") if reverse else float("inf"))
            return float(value)

        return sorted(rows, key=sort_key, reverse=reverse)
    return sorted(rows, key=lambda x: -(x["visibility_rate"] or 0))


def _paginate_prompt_rows(
    rows: list[dict[str, Any]],
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int, int, int]:
    safe_page, safe_page_size = _normalize_prompt_pagination(page, page_size)
    total = len(rows)
    start = (safe_page - 1) * safe_page_size
    return rows[start : start + safe_page_size], total, safe_page, safe_page_size


def _collect_prompt_metric_rows(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
) -> tuple[list[dict[str, Any]], Subject | None]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return [], None
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    pmap = {p.id: p for p in prompts}
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }

    by_prompt: dict[UUID, list] = defaultdict(list)
    by_prompt_all: dict[UUID, list] = defaultdict(list)
    for row in all_signals:
        by_prompt_all[row.prompt_id].append(row)
        if row.entity_id == entity.id:
            by_prompt[row.prompt_id].append(row)

    metric_rows: list[dict[str, Any]] = []
    for pid, subset in by_prompt.items():
        prompt = pmap.get(pid)
        topic = topics.get(prompt.topic_id) if prompt else None
        metrics = metrics_from_signals(
            subset,
            subject=subject,
            all_signals_for_voice=by_prompt_all.get(pid, []),
        )
        metric_rows.append(
            {
                "prompt_id": str(pid),
                "prompt_text": (prompt.text[:200] if prompt else ""),
                "topic_id": str(prompt.topic_id) if prompt else None,
                "topic_name": topic.name if topic else None,
                "funnel_stage": prompt.funnel_stage if prompt else None,
                "search_intent": prompt.search_intent if prompt else None,
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "sentiment_label": metrics.sentiment_label,
                "response_count": metrics.response_count,
            }
        )
    return metric_rows, subject


def build_prompts_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
    sort_by: str | None = None,
    order: str = "desc",
) -> list[dict[str, Any]]:
    metric_rows, _subject = _collect_prompt_metric_rows(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        entity_id=entity_id,
    )
    return _sort_prompt_metric_rows(metric_rows, sort_by=sort_by, order=order)


def build_prompts_performance_page(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    entity_id: str | None = None,
    sort_by: str | None = None,
    order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    metric_rows, _subject = _collect_prompt_metric_rows(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        entity_id=entity_id,
    )
    filtered = _apply_prompt_search(metric_rows, search)
    sorted_rows = _sort_prompt_metric_rows(filtered, sort_by=sort_by, order=order)
    items, total, safe_page, safe_page_size = _paginate_prompt_rows(
        sorted_rows,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def platform_performance_rows(
    all_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
) -> list[dict[str, Any]]:
    """Aggregate focus-entity KPIs by platform from in-memory signal rows."""
    by_platform_all: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    by_platform_entity: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in all_signals:
        by_platform_all[row.platform].append(row)
        if row.entity_id == entity_id:
            by_platform_entity[row.platform].append(row)

    out: list[dict[str, Any]] = []
    for platform_id, subset in by_platform_entity.items():
        metrics = metrics_from_signals(
            subset,
            subject=subject,
            all_signals_for_voice=by_platform_all.get(platform_id, []),
        )
        out.append(
            {
                "platform": platform_id,
                "visibility_rate": metrics.visibility_rate,
                "mention_rate": metrics.mention_rate,
                "share_voice": metrics.share_voice,
                "average_rank": metrics.average_rank,
                "citation_rate": metrics.citation_rate,
                "sentiment_score": metrics.sentiment_score,
                "sentiment_label": metrics.sentiment_label,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


def build_platform_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    subject = db.get(Subject, subject_id)
    if not subject:
        return []
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    return platform_performance_rows(all_signals, subject=subject, entity_id=entity.id)
