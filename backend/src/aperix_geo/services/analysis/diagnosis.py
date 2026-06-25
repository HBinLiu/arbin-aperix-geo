"""Diagnosis center: API entrypoints backed by SQL aggregation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis.entity import own_entity


def build_diagnosis_content_summary(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    """诊断内容汇总：综合得分与三维维度卡数据。"""
    from aperix_geo.services.analysis.diagnosis_sql import query_diagnosis_content_summary

    entity = own_entity(subject)
    summary = query_diagnosis_content_summary(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    return {
        "entity_id": entity.id,
        "entity_label": entity.label,
        "summary": summary,
    }


def build_diagnosis_content(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """诊断内容列表（分页）：按提示词聚合 AI 提及问题与品牌/来源差距。"""
    from aperix_geo.services.analysis.diagnosis_sql import query_diagnosis_content_page

    entity = own_entity(subject)
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    page_items, total = query_diagnosis_content_page(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        sort_by=sort_by,
        order=order,
        page=safe_page,
        page_size=safe_page_size,
    )

    return {
        "entity_id": entity.id,
        "entity_label": entity.label,
        "items": page_items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def build_diagnosis_content_detail(
    db: Session,
    *,
    subject: Subject,
    prompt_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    """Single prompt diagnosis content drill-down: gap summary + competitor breakdown."""
    from aperix_geo.services.analysis.diagnosis_sql import query_diagnosis_content_detail

    prompt = db.get(Prompt, prompt_id)
    if not prompt or prompt.subject_id != subject.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    result = query_diagnosis_content_detail(
        db,
        subject=subject,
        prompt=prompt,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    if int(result["brand"]["chat_mention_total"] or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses for prompt")
    return result
