"""Prompt detail page — single payload for KPI, charts, platforms, opportunity, responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import (
    daily_average_rank_series_from_index,
    daily_citation_share_series_from_signals,
    daily_share_series_from_index,
    mentioned_brands_for_response,
    metrics_from_signals,
)
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.diagnosis import (
    diagnosis_gap_metrics,
    diagnosis_mention_rate,
    has_diagnosis_content_gap,
    mention_action_priority,
    overall_action_priority,
)
from aperix_geo.services.analysis.performance import platform_performance_rows
from aperix_geo.services.analysis.signal_index import build_dual_signal_window
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_other_brand_signals, load_llm_response_signals
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.text import reply_text, truncate_text


def _signals_flat(index) -> list[LLMResponseSignalRow]:
    return [row for rows in index.by_date.values() for row in rows]


def _single_value_series(
    multi_series: list[dict[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    return [
        {"date": point["date"], "value": point["values"].get(label)}
        for point in multi_series
    ]


def _prompt_detail_platform_rows(
    all_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
) -> list[dict[str, Any]]:
    return [
        {
            "platform": row["platform"],
            "visibility_rate": row["visibility_rate"],
            "average_rank": row["average_rank"],
            "citation_rate": row["citation_rate"],
        }
        for row in platform_performance_rows(all_signals, subject=subject, entity_id=entity_id)
    ]


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
    gap = diagnosis_gap_metrics(
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
        signal = signal_by_response.get(row.id)
        if signal is None or not (signal.has_domain_link or signal.cited_on_source):
            continue
        mentioned = signal.mentioned
        rank = (
            round(float(signal.mention_rank), 1)
            if has_mention_rank(signal.mention_rank)
            else None
        )
        citation.append(
            {
                "response_id": str(row.id),
                "platform": row.platform,
                "reply_preview": truncate_text(reply_text(row.raw_text), 120, suffix="…"),
                "mentioned_brands": mentioned_brands_for_response(
                    row.id,
                    all_signals=all_signals,
                    entities=entities,
                ),
                "mentioned": mentioned,
                "rank": rank,
                "created_at": row.created_at.isoformat(),
                "cited_on_source": signal.cited_on_source,
            }
        )
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
    DB: 1× signals（含上期）+ 1× responses + 1× prompt/topic。
    """
    entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)

    prompt = db.get(Prompt, prompt_id)
    if prompt is None or prompt.subject_id != subject.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    topic = db.get(Topic, prompt.topic_id) if prompt.topic_id else None

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    other_brand_signals = load_llm_response_other_brand_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    windows = build_dual_signal_window(
        all_signals,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
    )
    focus_signals = windows.current.by_entity.get(entity.id, [])
    current_flat = _signals_flat(windows.current)
    mention_brand_signals = [
        *current_flat,
        *other_brand_signals,
    ]
    entities = list_analysis_entities(subject)

    metrics = metrics_from_signals(
        focus_signals,
        subject=subject,
        total_voice=windows.current.total_voice,
    )

    visibility_series = _single_value_series(
        daily_share_series_from_index(
            windows.current,
            entities=entities,
            metric="visibility",
            labels=[entity.label],
        ),
        entity.label,
    )
    average_rank_series = daily_average_rank_series_from_index(
        windows.current,
        entity_id=entity.id,
    )
    citation_series = _single_value_series(
        daily_citation_share_series_from_signals(current_flat, subject=subject),
        entity.label,
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
        "visibility_rate": metrics.visibility_rate,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "visibility_series": visibility_series,
        "average_rank_series": average_rank_series,
        "citation_series": citation_series,
        "platforms": _prompt_detail_platform_rows(current_flat, subject=subject, entity_id=entity.id),
        "opportunity": _opportunity_summary(
            focus_signals,
            subject=subject,
            all_signals=current_flat,
            focus_entity_id=entity.id,
        ),
        "citation_responses": citation_responses,
    }
