"""Topic, prompt, and platform performance tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.entity import resolve_analysis_entity
from aperix_geo.services.analysis.grouped_sql import (
    query_platform_metrics,
    query_prompt_metrics,
    query_topic_metrics,
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
    topics, _prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject_id)
    return query_topic_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        topics=topics,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )


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
    safe_page, safe_page_size = normalize_pagination(page, page_size)
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
    topics, prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject_id)
    topic_map = topics
    rows = query_prompt_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        prompts=prompts,
        topics=topic_map,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    return rows, subject


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
    return query_platform_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
