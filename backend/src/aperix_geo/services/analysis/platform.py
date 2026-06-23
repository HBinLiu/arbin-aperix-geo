"""Platform analysis page — flattened payload."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.grouped_sql import (
    query_platform_charts,
    query_platform_matrix,
    query_platform_metrics,
)
from aperix_geo.services.sampling.platforms import resolve_platforms_for_sampling


def build_platform_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
    matrix_row: str = "competitor",
) -> dict[str, Any]:
    """平台页扁平化数据：矩阵单元 / 平台排名 / 分指标多平台趋势。"""
    focus_entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    platform_ids = resolve_platforms_for_sampling(subject, platform)
    entities = list_analysis_entities(subject)

    matrix_kwargs = {
        "row_dimension": matrix_row,
        "platform_ids": platform_ids,
        "platform": platform,
        "topic_id": topic_id,
    }
    matrix_cells = query_platform_matrix(
        db,
        subject=subject,
        entities=entities,
        focus_entity=focus_entity,
        dt_from=dt_from,
        dt_to=dt_to,
        **matrix_kwargs,
    )
    matrix_cells_previous = query_platform_matrix(
        db,
        subject=subject,
        entities=entities,
        focus_entity=focus_entity,
        dt_from=prev_from,
        dt_to=prev_to,
        **matrix_kwargs,
    )

    return {
        "entity_id": focus_entity.id,
        "matrix_row": matrix_row,
        "matrix_cells": {
            "current": matrix_cells,
            "previous": matrix_cells_previous,
        },
        "performance": {
            "current": query_platform_metrics(
                db,
                subject=subject,
                entity_id=focus_entity.id,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
            ),
            "previous": query_platform_metrics(
                db,
                subject=subject,
                entity_id=focus_entity.id,
                dt_from=prev_from,
                dt_to=prev_to,
                platform=platform,
                topic_id=topic_id,
            ),
        },
        "charts": query_platform_charts(
            db,
            subject=subject,
            entity_id=focus_entity.id,
            platform_ids=platform_ids,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        ),
    }
