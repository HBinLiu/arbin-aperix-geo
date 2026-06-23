"""Diagnosis center: priorities and content gap analysis."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationUrl, Prompt, Subject
from aperix_geo.services.analysis._query import subject_response_window
from aperix_geo.services.analysis.aggregate import metrics_from_signals
from aperix_geo.services.analysis.entity import list_analysis_entities, own_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.utils.net import host_from, host_under_root


ACTION_PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def mention_action_priority(mention_rate: float | None, average_rank: float | None) -> str:
    """AI 提及率行动优先级：衡量自有品牌绝对曝光健康度。"""
    issue = diagnosis_issue_type(mention_rate, average_rank)
    if issue == "not_mentioned":
        return "high"
    if issue in ("low_mention", "poor_rank"):
        return "medium"
    return "low"


def gap_action_priority(gap_rate: float) -> str:
    """品牌/来源差距行动优先级：衡量相对竞品落后程度。"""
    if gap_rate >= 0.8:
        return "high"
    if gap_rate >= 0.5:
        return "medium"
    return "low"


def mention_has_issue(mention_rate: float | None, average_rank: float | None) -> bool:
    """AI 提及率是否存在需行动的问题（非 healthy）。"""
    return mention_action_priority(mention_rate, average_rank) != "low"


def diagnosis_mention_rate(
    *,
    mention_own_count: int,
    mention_total_count: int,
    visibility_rate: float | None = None,
) -> float:
    """诊断口径 AI 提及率：被提及回复数 / 分析回复数（0~1，与表格副文案一致）。"""
    if visibility_rate is not None:
        return visibility_rate
    if mention_total_count <= 0:
        return 0.0
    return round(mention_own_count / mention_total_count, 4)


def has_diagnosis_content_gap(
    *,
    brand_gap_rate: float,
    source_gap_rate: float,
    mention_rate: float | None = None,
    average_rank: float | None = None,
    mention_priority: str | None = None,
) -> bool:
    """诊断内容表入表条件：品牌/来源差距，或 AI 提及率问题。"""
    if brand_gap_rate > 0 or source_gap_rate > 0:
        return True
    if mention_priority is not None:
        return mention_priority != "low"
    return mention_has_issue(mention_rate, average_rank)


def overall_action_priority(*priorities: str) -> str:
    """总优先级：取 AI 提及、品牌差距、来源差距行动优先级之最紧急者。"""
    return min(priorities, key=lambda key: ACTION_PRIORITY_ORDER.get(key, 9))


def diagnosis_issue_type(mention_rate: float | None, average_rank: float | None) -> str:
    rate = mention_rate or 0
    if rate <= 0:
        return "not_mentioned"
    if rate < 0.5:
        return "low_mention"
    if average_rank is not None and average_rank > 3:
        return "poor_rank"
    return "healthy"


def priority_counts(items: list[dict[str, Any]], *, key: str = "priority") -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        value = item.get(key)
        if value in counts:
            counts[value] += 1
    return counts


def health_score_from_mention(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    total = sum((item.get("mention_rate") or 0) for item in items)
    return round(total / len(items) * 100, 1)


def overall_diagnosis_status(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "improvement"
    return "critical"


def _competitor_ids(entities: list, focus_entity_id: str) -> set[str]:
    return {entity.id for entity in entities if entity.id != focus_entity_id}


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


def diagnosis_gap_metrics(
    *,
    focus_entity_id: str,
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
) -> dict[str, Any]:
    """Brand/source gap within a reply pool.

    Brand: among replies where any competitor is mentioned, share where own brand is not mentioned.
    Source: among replies where any competitor has a domain citation link, share where own brand does not.
    """
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
    competitor_ids = _competitor_ids(entities, focus_entity_id)
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


def _apply_diagnosis_row_priorities(item: dict[str, Any]) -> None:
    item["priority"] = overall_action_priority(
        item.get("mention_priority", "low"),
        item.get("brand_gap_priority", "low"),
        item.get("source_gap_priority", "low"),
    )


def _refresh_gap_priorities(item: dict[str, Any]) -> None:
    item["brand_gap_priority"] = gap_action_priority(item["brand_gap_rate"])
    item["source_gap_priority"] = gap_action_priority(item["source_gap_rate"])


def health_score_from_gap(gap_rates: list[float]) -> float:
    """Average ``(1 - gap_rate)`` over the given rates (caller filters to gap > 0 prompts)."""
    if not gap_rates:
        return 0.0
    avg_gap = sum(gap_rates) / len(gap_rates)
    return round(max(0.0, (1 - avg_gap) * 100), 1)


def health_score_from_gap_items(items: list[dict[str, Any]], *, gap_key: str) -> float:
    """Health score for a gap dimension; denominator = prompts where ``gap_key > 0``."""
    gap_rates = [float(row[gap_key]) for row in items if float(row.get(gap_key) or 0) > 0]
    return health_score_from_gap(gap_rates)


def build_diagnosis_content_summary(
    db: Session,
    *,
    subject: Subject,
) -> dict[str, Any]:
    """诊断内容汇总：综合得分与三维维度卡数据。"""
    from aperix_geo.services.analysis.diagnosis_page import query_diagnosis_content_summary

    entity = own_entity(subject)
    dt_from, dt_to = subject_response_window(db, subject=subject)
    summary = query_diagnosis_content_summary(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
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
    sort_by: str | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """诊断内容列表（分页）：按提示词聚合 AI 提及问题与品牌/来源差距。"""
    from aperix_geo.services.analysis.diagnosis_page import query_diagnosis_content_page

    entity = own_entity(subject)
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    dt_from, dt_to = subject_response_window(db, subject=subject)
    page_items, total = query_diagnosis_content_page(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
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


def _build_diagnosis_content_summary(
    *,
    mention_snapshots: list[dict[str, Any]],
    gap_items: list[dict[str, Any]],
) -> dict[str, Any]:
    empty_counts = {"high": 0, "medium": 0, "low": 0}
    if not mention_snapshots and not gap_items:
        return {
            "overall_score": 0.0,
            "overall_status": "critical",
            "mention": {"health_score": 0.0, "priority_counts": dict(empty_counts)},
            "brand_gap": {"health_score": 0.0, "priority_counts": dict(empty_counts)},
            "source_gap": {"health_score": 0.0, "priority_counts": dict(empty_counts)},
        }

    mention_health = health_score_from_mention(mention_snapshots)
    brand_gap_items = [row for row in gap_items if row["brand_gap_rate"] > 0]
    source_gap_items = [row for row in gap_items if row["source_gap_rate"] > 0]
    brand_gap_health = health_score_from_gap_items(gap_items, gap_key="brand_gap_rate")
    source_gap_health = health_score_from_gap_items(gap_items, gap_key="source_gap_rate")
    overall_score = round(mention_health * 0.4 + brand_gap_health * 0.3 + source_gap_health * 0.3, 1)

    return {
        "overall_score": overall_score,
        "overall_status": overall_diagnosis_status(overall_score),
        "mention": {
            "health_score": mention_health,
            "priority_counts": priority_counts(gap_items, key="mention_priority"),
        },
        "brand_gap": {
            "health_score": brand_gap_health,
            "priority_counts": priority_counts(brand_gap_items, key="brand_gap_priority"),
        },
        "source_gap": {
            "health_score": source_gap_health,
            "priority_counts": priority_counts(source_gap_items, key="source_gap_priority"),
        },
    }


def _merge_gap_counts(
    existing: dict[str, Any],
    item: dict[str, Any],
    *,
    gap_key: str,
    own_key: str,
    total_key: str,
) -> None:
    if item[gap_key] > existing[gap_key]:
        existing[gap_key] = item[gap_key]
        existing[own_key] = item[own_key]
        existing[total_key] = item[total_key]


def _response_ids_by_platform(
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
) -> dict[str, set[UUID]]:
    by_platform: dict[str, set[UUID]] = defaultdict(set)
    for row in entity_signals:
        if row.response_id in response_ids:
            by_platform[row.platform].add(row.response_id)
    return by_platform


def _merged_diagnosis_gap_metrics(
    *,
    focus_entity_id: str,
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
) -> dict[str, Any]:
    """Per-platform gap, then take max gap and its reply counts."""
    by_platform = _response_ids_by_platform(entity_signals, response_ids)
    if not by_platform:
        return {
            **diagnosis_gap_metrics(
                focus_entity_id=focus_entity_id,
                response_ids=set(),
                all_signals=all_signals,
                subject=subject,
            ),
            "platforms": [],
        }

    merged: dict[str, Any] | None = None
    for platform in sorted(by_platform.keys()):
        gap = diagnosis_gap_metrics(
            focus_entity_id=focus_entity_id,
            response_ids=by_platform[platform],
            all_signals=all_signals,
            subject=subject,
        )
        if gap["brand_gap_rate"] <= 0 and gap["source_gap_rate"] <= 0:
            continue
        if merged is None:
            merged = {**gap, "platforms": [platform]}
            continue
        if platform not in merged["platforms"]:
            merged["platforms"].append(platform)
        _merge_gap_counts(
            merged,
            gap,
            gap_key="brand_gap_rate",
            own_key="brand_own_count",
            total_key="brand_total_count",
        )
        _merge_gap_counts(
            merged,
            gap,
            gap_key="source_gap_rate",
            own_key="source_own_count",
            total_key="source_total_count",
        )
        _refresh_gap_priorities(merged)

    if merged is not None:
        return merged

    gap = diagnosis_gap_metrics(
        focus_entity_id=focus_entity_id,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
    )
    return {**gap, "platforms": []}


def _platforms_with_gap(
    *,
    focus_entity_id: str,
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
    metric: Literal["brand", "source"],
) -> set[str]:
    """Platforms where own brand has a positive gap for the given metric."""
    gap_key = "brand_gap_rate" if metric == "brand" else "source_gap_rate"
    by_platform = _response_ids_by_platform(entity_signals, response_ids)
    return {
        platform
        for platform, pool in by_platform.items()
        if diagnosis_gap_metrics(
            focus_entity_id=focus_entity_id,
            response_ids=pool,
            all_signals=all_signals,
            subject=subject,
        )[gap_key]
        > 0
    }


def _distinct_competitors_with_signal(
    all_signals: list[LLMResponseSignalRow],
    *,
    response_ids: set[UUID],
    competitor_ids: set[str],
    signal_present,
) -> int:
    seen: set[str] = set()
    for row in all_signals:
        if row.response_id not in response_ids or row.entity_id not in competitor_ids:
            continue
        if signal_present(row):
            seen.add(row.entity_id)
    return len(seen)


def _total_mention_count(
    all_signals: list[LLMResponseSignalRow],
    *,
    response_ids: set[UUID],
    catalog_ids: set[str],
) -> int:
    total = 0
    for row in all_signals:
        if row.response_id not in response_ids or row.entity_id not in catalog_ids:
            continue
        total += row.mention_count
    return total


def _total_domain_link_count(
    all_signals: list[LLMResponseSignalRow],
    *,
    response_ids: set[UUID],
    catalog_ids: set[str],
) -> int:
    return sum(
        1
        for row in all_signals
        if row.response_id in response_ids
        and row.entity_id in catalog_ids
        and row.has_domain_link
    )


def _distinct_competitor_domains_with_link(
    all_signals: list[LLMResponseSignalRow],
    *,
    response_ids: set[UUID],
    competitor_ids: set[str],
    domain_key_by_entity: dict[str, str],
) -> int:
    seen: set[str] = set()
    for row in all_signals:
        if row.response_id not in response_ids or row.entity_id not in competitor_ids:
            continue
        if not row.has_domain_link:
            continue
        key = domain_key_by_entity.get(row.entity_id, "")
        if key:
            seen.add(key)
    return len(seen)


def _lookup_entity_citation_urls(
    db: Session,
    *,
    response_ids: set[UUID],
    domain: str | None,
    label: str,
) -> list[str]:
    if not response_ids:
        return []
    root = (domain or label or "").strip().lower()
    if not root:
        return []
    execute = getattr(db, "execute", None)
    if execute is None:
        return []
    rows = execute(
        select(CitationUrl.url)
        .where(CitationUrl.response_id.in_(response_ids))
        .order_by(CitationUrl.url.asc())
    ).scalars().all()
    seen: set[str] = set()
    urls: list[str] = []
    for url in rows:
        text = str(url or "").strip()
        if not text or text in seen:
            continue
        host = host_from(text)
        if host and host_under_root(host, root):
            seen.add(text)
            urls.append(text)
    return urls


def _competitor_breakdown_rows(
    db: Session,
    all_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    focus_entity_id: str,
    response_ids: set[UUID],
    gap_platforms: set[str],
    metric: Literal["brand", "source"],
) -> list[dict[str, Any]]:
    
    if not gap_platforms:
        return []

    entities = [entity for entity in list_analysis_entities(subject) if entity.id != focus_entity_id]
    platform_values = sorted(gap_platforms)
    allowed_platforms = gap_platforms
    gap_response_ids = {
        row.response_id
        for row in all_signals
        if row.response_id in response_ids and row.platform in allowed_platforms
    }
    if not gap_response_ids:
        return []

    pool_signals = [row for row in all_signals if row.response_id in gap_response_ids]

    rows: list[dict[str, Any]] = []
    for entity in entities:
        subset = [
            row
            for row in all_signals
            if row.entity_id == entity.id
            and row.response_id in gap_response_ids
            and row.platform in allowed_platforms
        ]
        if not subset:
            continue

        if metric == "brand":
            metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=pool_signals)
            contribution_rate = metrics.visibility_rate
            average_rank = metrics.average_rank
        else:
            linked_rows = sum(1 for row in subset if row.has_domain_link)
            n = len({row.response_id for row in subset})
            contribution_rate = round(linked_rows / n, 4) if n else 0.0
            average_rank = None

        if not contribution_rate or contribution_rate <= 0:
            continue

        entity_platforms: list[str] = []
        for platform in platform_values:
            platform_subset = [row for row in subset if row.platform == platform]
            if not platform_subset:
                continue
            if metric == "brand":
                platform_metrics = metrics_from_signals(
                    platform_subset,
                    subject=subject,
                    all_signals_for_voice=pool_signals,
                )
                if platform_metrics.visibility_rate and platform_metrics.visibility_rate > 0:
                    entity_platforms.append(platform)
            elif any(row.has_domain_link for row in platform_subset):
                entity_platforms.append(platform)

        if not entity_platforms:
            continue

        row_payload: dict[str, Any] = {
            "entity_id": entity.id,
            "label": entity.label,
            "display_name": entity.display_name,
            "domain": entity.domain or None,
            "platforms": entity_platforms,
            "contribution_rate": contribution_rate,
            "average_rank": average_rank,
        }
        if metric == "source":
            linked_response_ids = {
                row.response_id for row in subset if row.has_domain_link
            }
            row_payload["citation_urls"] = _lookup_entity_citation_urls(
                db,
                response_ids=linked_response_ids,
                domain=entity.domain,
                label=entity.label,
            )

        rows.append(row_payload)

    rows.sort(
        key=lambda row: (
            row["average_rank"] if row["average_rank"] is not None else 999,
            -(row["contribution_rate"] or 0),
            row["label"],
        )
    )
    return rows


def _own_mentioned_response_count(entity_signals: list[LLMResponseSignalRow]) -> int:
    return len({row.response_id for row in entity_signals if row.mentioned})


def _chat_mention_counts(
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
) -> tuple[int, int]:
    """Own-brand mention coverage across all analyzed replies (not the gap pool)."""
    return _own_mentioned_response_count(entity_signals), len(response_ids)


def build_diagnosis_content_detail(
    db: Session,
    *,
    subject: Subject,
    prompt_id: UUID,
) -> dict[str, Any]:
    """Single prompt diagnosis content drill-down: gap summary + competitor breakdown."""
    from aperix_geo.services.analysis.diagnosis_page import query_diagnosis_content_detail

    dt_from, dt_to = subject_response_window(db, subject=subject)
    prompt = db.get(Prompt, prompt_id)
    if not prompt or prompt.subject_id != subject.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    result = query_diagnosis_content_detail(
        db,
        subject=subject,
        prompt=prompt,
        dt_from=dt_from,
        dt_to=dt_to,
    )
    if int(result["brand"]["chat_mention_total"] or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses for prompt")
    return result
