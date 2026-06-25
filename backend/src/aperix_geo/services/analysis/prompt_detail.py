"""Prompt detail page — single payload for KPI, charts, platforms, opportunity, responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._rows import build_citation_response_row
from aperix_geo.services.analysis._series import previous_date_range, single_value_series
from aperix_geo.services.analysis.aggregate import metrics_from_signals
from aperix_geo.services.analysis.diagnosis_rules import (
    diagnosis_mention_rate,
    gap_action_priority,
    has_diagnosis_content_gap,
    mention_action_priority,
    overall_action_priority,
)
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.entity_sql import (
    daily_average_rank_series_for_window,
    daily_citation_share_series_for_window,
    daily_share_series_for_window,
    query_dual_entity_window,
)
from aperix_geo.services.analysis.grouped_sql import query_platform_metrics
from aperix_geo.services.analysis.signal_load import (
    LLMResponseSignalRow,
    load_llm_response_signals,
    load_mention_brand_signals,
)


def _response_ids_with_competitor_signal(
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    competitor_ids: set[str],
    *,
    has_signal,
) -> set[UUID]:
    present: set[UUID] = set()
    for row in all_signals:
        if row.response_id not in response_ids or row.entity_id not in competitor_ids:
            continue
        if has_signal(row):
            present.add(row.response_id)
    return present


def _own_signal_count_in_responses(
    focus_rows: list[LLMResponseSignalRow],
    response_ids: set[UUID],
    *,
    has_signal,
) -> int:
    return sum(
        1
        for row in focus_rows
        if row.response_id in response_ids and has_signal(row)
    )


def _competitors_in_pool(
    entities: list,
    *,
    focus_entity_id: str,
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    has_signal,
) -> list[str]:
    catalog_order = {entity.label: index for index, entity in enumerate(entities)}
    labels: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        if entity.id == focus_entity_id:
            continue
        if not any(
            has_signal(row)
            for row in all_signals
            if row.response_id in response_ids and row.entity_id == entity.id
        ):
            continue
        label = entity.label
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return sorted(labels, key=lambda item: catalog_order.get(item, 10_000))


def _diagnosis_gap_metrics(
    *,
    focus_entity_id: str,
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
) -> dict[str, Any]:
    """Brand/source gap within a reply pool (prompt detail opportunity card)."""
    if not response_ids:
        return {
            "brand_gap_rate": 0.0,
            "brand_gap_priority": "low",
            "source_gap_rate": 0.0,
            "source_gap_priority": "low",
            "competitors": [],
            "brand_own_count": 0,
            "brand_total_count": 0,
            "source_own_count": 0,
            "source_total_count": 0,
        }

    entities = list_analysis_entities(subject)
    competitor_ids = {entity.id for entity in entities if entity.id != focus_entity_id}
    focus_rows = [
        row
        for row in all_signals
        if row.response_id in response_ids and row.entity_id == focus_entity_id
    ]

    brand_pool = _response_ids_with_competitor_signal(
        response_ids,
        all_signals,
        competitor_ids,
        has_signal=lambda row: row.mentioned,
    )
    brand_total = len(brand_pool)
    brand_own = _own_signal_count_in_responses(
        focus_rows,
        brand_pool,
        has_signal=lambda row: row.mentioned,
    )
    brand_gap_rate = round(1 - brand_own / brand_total, 4) if brand_total else 0.0

    source_pool = _response_ids_with_competitor_signal(
        response_ids,
        all_signals,
        competitor_ids,
        has_signal=lambda row: row.has_domain_link,
    )
    source_total = len(source_pool)
    source_own = _own_signal_count_in_responses(
        focus_rows,
        source_pool,
        has_signal=lambda row: row.has_domain_link,
    )
    source_gap_rate = round(1 - source_own / source_total, 4) if source_total else 0.0

    brand_competitors = _competitors_in_pool(
        entities,
        focus_entity_id=focus_entity_id,
        response_ids=response_ids,
        all_signals=all_signals,
        has_signal=lambda row: row.mentioned,
    )
    source_competitors = _competitors_in_pool(
        entities,
        focus_entity_id=focus_entity_id,
        response_ids=response_ids,
        all_signals=all_signals,
        has_signal=lambda row: row.has_domain_link,
    )
    competitors: list[str] = []
    seen: set[str] = set()
    catalog_order = {entity.label: index for index, entity in enumerate(entities)}
    for label in sorted(
        {*brand_competitors, *source_competitors},
        key=lambda item: catalog_order.get(item, 10_000),
    ):
        if label not in seen:
            seen.add(label)
            competitors.append(label)

    return {
        "brand_gap_rate": brand_gap_rate,
        "brand_gap_priority": gap_action_priority(brand_gap_rate),
        "source_gap_rate": source_gap_rate,
        "source_gap_priority": gap_action_priority(source_gap_rate),
        "competitors": competitors,
        "brand_own_count": brand_own,
        "brand_total_count": brand_total,
        "source_own_count": source_own,
        "source_total_count": source_total,
    }


def _metrics_from_entity_row(entity_rows: list[dict[str, Any]], entity_id: str) -> dict[str, Any]:
    row = next((item for item in entity_rows if item["id"] == entity_id), None)
    if row is None:
        return {}
    return row.get("metrics") or {}


def _opportunity_summary(
    entity_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    all_signals: list[LLMResponseSignalRow],
    focus_entity_id: str,
) -> dict[str, Any] | None:
    if not entity_signals:
        return None

    response_ids = {row.response_id for row in entity_signals}
    gap = _diagnosis_gap_metrics(
        focus_entity_id=focus_entity_id,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
    )
    metrics = metrics_from_signals(
        entity_signals,
        subject=subject,
        all_signals_for_voice=all_signals,
    )
    mention_priority = mention_action_priority(
        diagnosis_mention_rate(
            mention_own_count=sum(1 for row in entity_signals if row.mentioned),
            mention_total_count=metrics.response_count,
            visibility_rate=metrics.visibility_rate,
        ),
        metrics.average_rank,
    )
    if not has_diagnosis_content_gap(
        brand_gap_rate=gap["brand_gap_rate"],
        source_gap_rate=gap["source_gap_rate"],
        mention_priority=mention_priority,
    ):
        return None

    return {
        "brand_gap_rate": gap["brand_gap_rate"],
        "brand_gap_priority": gap["brand_gap_priority"],
        "source_gap_rate": gap["source_gap_rate"],
        "source_gap_priority": gap["source_gap_priority"],
        "mention_priority": mention_priority,
        "priority": overall_action_priority(
            mention_priority,
            gap["brand_gap_priority"],
            gap["source_gap_priority"],
        ),
    }


def _citation_response_rows(
    rows,
    *,
    signal_by_response: dict[UUID, LLMResponseSignalRow],
    all_signals: list[LLMResponseSignalRow],
    entities: list,
) -> list[dict[str, Any]]:
    citation: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: item.created_at, reverse=True):
        item = build_citation_response_row(
            row,
            signal_by_response.get(row.id),
            all_signals=all_signals,
            entities=entities,
        )
        if item is not None:
            citation.append(item)
    return citation


def build_prompt_detail(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    prompt_id: UUID,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """提示词详情页扁平化数据：指标 / 趋势 / 平台 / 机会 / 引用回复明细。

    聊天回复明细见 ``POST .../analysis/responses``（传 prompt_id）。
    KPI / 趋势 / 平台走 SQL；引用与机会仍按单 prompt 窗口加载 signal。
    """
    entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)

    prompt = db.get(Prompt, prompt_id)
    if prompt is None or prompt.subject_id != subject.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    topic = db.get(Topic, prompt.topic_id) if prompt.topic_id else None

    entities = list_analysis_entities(subject)
    windows = query_dual_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        entities=entities,
    )
    current = windows["current"]
    focus_metrics = _metrics_from_entity_row(current.entity_rows, entity.id)

    visibility_series = single_value_series(
        daily_share_series_for_window(
            current,
            entities=entities,
            metric="visibility",
            labels=[entity.label],
        ),
        entity.label,
    )
    average_rank_series = daily_average_rank_series_for_window(
        current,
        entity_id=entity.id,
    )
    citation_series = single_value_series(
        daily_citation_share_series_for_window(
            current,
            entities=entities,
            labels=[entity.label],
        ),
        entity.label,
    )
    platform_rows = query_platform_metrics(
        db,
        subject=subject,
        entity_id=entity.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    platforms = [
        {
            "platform": row["platform"],
            "visibility_rate": row["visibility_rate"],
            "average_rank": row["average_rank"],
            "citation_rate": row["citation_rate"],
        }
        for row in platform_rows
    ]

    current_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    focus_signals = [row for row in current_signals if row.entity_id == entity.id]
    mention_brand_signals = load_mention_brand_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )

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
    citation_responses = _citation_response_rows(
        response_rows,
        signal_by_response=signal_by_response,
        all_signals=mention_brand_signals,
        entities=entities,
    )

    return {
        "entity_id": entity.id,
        "entity_label": entity.label,
        "prompt_id": str(prompt_id),
        "prompt_text": prompt.text,
        "topic_id": str(prompt.topic_id) if prompt.topic_id else None,
        "topic_name": topic.name if topic else None,
        "search_intent": prompt.search_intent,
        "visibility_rate": focus_metrics.get("visibility_rate"),
        "average_rank": focus_metrics.get("average_rank"),
        "citation_rate": focus_metrics.get("citation_rate"),
        "visibility_series": visibility_series,
        "average_rank_series": average_rank_series,
        "citation_series": citation_series,
        "platforms": platforms,
        "opportunity": _opportunity_summary(
            focus_signals,
            subject=subject,
            all_signals=current_signals,
            focus_entity_id=entity.id,
        ),
        "citation_responses": citation_responses,
    }
