"""Aggregate analysis payloads for on-demand brand reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._page import build_rank_table_rows, metric_with_rank, previous_value
from aperix_geo.services.analysis._query import count_responses_in_window
from aperix_geo.services.analysis._series import previous_date_range
from aperix_geo.services.analysis.aggregate import rank_dict_from_entity_rows
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.analysis.dashboard import build_dashboard_overview
from aperix_geo.services.analysis.diagnosis_sql import (
    query_diagnosis_content_page,
    query_diagnosis_content_summary,
)
from aperix_geo.services.analysis.entity import (
    competitor_entities,
    entity_display_name,
    list_analysis_entities,
    own_entity,
    resolve_analysis_entity,
)
from aperix_geo.services.analysis.entity_sql import query_dual_entity_window
from aperix_geo.services.analysis.grouped_sql import query_platform_metrics
from aperix_geo.services.report.favicon import favicon_data_url
from aperix_geo.services.report.platform import platform_logo_data_url
from aperix_geo.services.sampling.llm import list_sampling_platforms
from aperix_geo.services.sampling.platforms import resolve_platforms_for_sampling

def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _platform_label(platform_key: str) -> str:
    labels = {item["platform"]: item["label"] for item in list_sampling_platforms()}
    return labels.get(platform_key, platform_key.replace("_", " ").title())


def _avg(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _build_key_insight(
    *,
    brand: str,
    overview: dict[str, Any],
    summary: dict[str, Any] | None,
) -> str:
    visibility = overview.get("visibility") or {}
    current = visibility.get("current")
    rank = visibility.get("rank")
    overall = float((summary or {}).get("overall_score") or 0)

    vis_text = f"{current * 100:.1f}%" if current is not None else "—"
    rank_text = f"第 {rank} 名" if rank else "暂无排名"

    if overall >= 80:
        tone = "整体表现优秀，可继续巩固优势场景。"
    elif overall >= 60:
        tone = "整体表现良好，建议优先处理高优先级内容缺口。"
    elif overall >= 40:
        tone = "部分维度需要重点关注，建议从提及率与品牌差距入手优化。"
    else:
        tone = "多项指标亟需改善，建议尽快补齐高意图 Prompt 覆盖。"

    return (
        f"{brand} 在选定周期内 AI 可见度 {vis_text}（{rank_text}）。"
        f"内容诊断综合得分 {overall:.0f}，{tone}"
    )


def _build_report_context(
    db: Session,
    *,
    subject: Subject,
    own_label: str,
    overview: dict[str, Any],
    diagnosis_summary: dict[str, Any] | None,
    dt_from: datetime,
    dt_to: datetime,
    entity_id: str | None,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> dict[str, Any]:
    entities = list_analysis_entities(subject)
    focus_entity = resolve_analysis_entity(subject, entity_id)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)

    windows = query_dual_entity_window(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        prev_from=prev_from,
        prev_to=prev_to,
        platform=platform,
        topic_id=topic_id,
        entities=entities,
    )
    current = windows["current"]
    previous = windows["previous"]
    has_previous = previous.has_data
    rank = rank_dict_from_entity_rows(current.entity_rows, own_label=own_label)
    previous_rank = rank_dict_from_entity_rows(previous.entity_rows, own_label=own_label)

    focus_current_row = next((row for row in current.entity_rows if row["id"] == focus_entity.id), None)
    focus_previous_row = next((row for row in previous.entity_rows if row["id"] == focus_entity.id), None)
    focus_current = (focus_current_row or {}).get("metrics") or {}
    focus_previous = (focus_previous_row or {}).get("metrics") or {}
    mention_metric = metric_with_rank(
        focus_current.get("mention_rate"),
        previous_value(focus_previous.get("mention_rate"), has_previous=has_previous),
        rank.get("mention_rate") or {},
        focus_entity.label,
    )
    average_rank_metric = metric_with_rank(
        focus_current.get("average_rank"),
        previous_value(focus_previous.get("average_rank"), has_previous=has_previous),
        rank.get("average_rank") or {},
        focus_entity.label,
    )

    visibility_table = overview.get("visibility_table") or []
    competitor_rows = [row for row in visibility_table if row.get("id") != own_label]

    topics, prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject.id)
    platform_ids = resolve_platforms_for_sampling(subject, platform)
    platform_metrics = query_platform_metrics(
        db,
        subject=subject,
        entity_id=focus_entity.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    diagnosis_items, _total = query_diagnosis_content_page(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        sort_by="priority",
        order="asc",
        page=1,
        page_size=8,
    )

    return {
        "mention_metric": mention_metric,
        "average_rank_metric": average_rank_metric,
        "competitors": [
            {
                "label": entity_display_name(entity),
                "domain": entity.domain,
                "logo": favicon_data_url(entity.domain),
            }
            for entity in competitor_entities(subject)[:6]
        ],
        "platforms": [
            {
                "key": platform_key,
                "label": _platform_label(platform_key),
                "logo": platform_logo_data_url(platform_key),
            }
            for platform_key in platform_ids
        ],
        "topic_count": len(topics),
        "prompt_count": len(prompts),
        "platform_metrics": platform_metrics,
        "citation_table": build_rank_table_rows(
            rank.get("citation_share") or {},
            previous_rank.get("citation_share") or {},
            entities=entities,
            has_previous=has_previous,
        ),
        "share_voice_table": build_rank_table_rows(
            rank.get("share_voice") or {},
            previous_rank.get("share_voice") or {},
            entities=entities,
            has_previous=has_previous,
        ),
        "diagnosis_items": diagnosis_items,
        "competitor_avg": {
            "visibility": _avg([row.get("cur_value") for row in competitor_rows]),
            "mention": _avg(
                [
                    row.get("cur_value")
                    for row in build_rank_table_rows(
                        rank.get("mention_rate") or {},
                        previous_rank.get("mention_rate") or {},
                        entities=entities,
                        has_previous=has_previous,
                    )
                    if row.get("id") != own_label
                ]
            ),
            "citation": _avg(
                [
                    row.get("cur_value")
                    for row in build_rank_table_rows(
                        rank.get("citation_share") or {},
                        previous_rank.get("citation_share") or {},
                        entities=entities,
                        has_previous=has_previous,
                    )
                    if row.get("id") != own_label
                ]
            ),
            "share_voice": _avg(
                [
                    row.get("cur_value")
                    for row in build_rank_table_rows(
                        rank.get("share_voice") or {},
                        previous_rank.get("share_voice") or {},
                        entities=entities,
                        has_previous=has_previous,
                    )
                    if row.get("id") != own_label
                ]
            ),
            "average_rank": _avg(
                [
                    row.get("cur_value")
                    for row in build_rank_table_rows(
                        rank.get("average_rank") or {},
                        previous_rank.get("average_rank") or {},
                        entities=entities,
                        has_previous=has_previous,
                    )
                    if row.get("id") != own_label
                ]
            ),
        },
        "key_insight": _build_key_insight(
            brand=entity_display_name(own_entity(subject)),
            overview=overview,
            summary=diagnosis_summary,
        ),
        "focus_entity_label": focus_entity.label,
    }


def build_brand_report_payload(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    entity_id: str | None = None,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    """Build report snapshot for an arbitrary analysis window."""
    own = own_entity(subject)
    entity = resolve_analysis_entity(subject, entity_id)
    overview = build_dashboard_overview(
        db,
        subject=subject,
        entity_id=entity_id,
        platform=platform,
        topic_id=topic_id,
        dt_from=dt_from,
        dt_to=dt_to,
    )
    diagnosis_summary = query_diagnosis_content_summary(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    response_count = count_responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    context = _build_report_context(
        db,
        subject=subject,
        own_label=own.label,
        overview=overview,
        diagnosis_summary=diagnosis_summary,
        dt_from=dt_from,
        dt_to=dt_to,
        entity_id=entity_id,
        platform=platform,
        topic_id=topic_id,
    )
    mention_metric = context.pop("mention_metric")
    average_rank_metric = context.pop("average_rank_metric")
    if "mention" not in overview:
        overview = {**overview, "mention": mention_metric}
    if "average_rank" not in overview:
        overview = {**overview, "average_rank": average_rank_metric}
    competitor_avg = context.get("competitor_avg") or {}
    if "mention" not in competitor_avg:
        context["competitor_avg"] = {**competitor_avg, "mention": None}
    competitor_avg = context.get("competitor_avg") or {}
    if "average_rank" not in competitor_avg:
        context["competitor_avg"] = {**competitor_avg, "average_rank": None}

    return {
        "meta": {
            "brand": entity_display_name(own),
            "domain": own.domain,
            "logo": favicon_data_url(own.domain),
            "subject_id": str(subject.id),
            "entity_id": entity.id,
            "entity_label": entity.label,
            "own_entity_label": own.label,
            "period_start": _iso(dt_from),
            "period_end": _iso(dt_to),
            "generated_at": _iso(datetime.now(UTC)),
            "response_count": response_count,
        },
        "overview": overview,
        "diagnosis": {
            "entity_id": own.id,
            "entity_label": own.label,
            "summary": diagnosis_summary,
        },
        "context": context,
    }
