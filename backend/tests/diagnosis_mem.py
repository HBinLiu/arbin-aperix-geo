"""In-memory diagnosis content queries for unit tests (replaces deleted _load_diagnosis_content_merged)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis.aggregate import metrics_from_signals
from aperix_geo.services.analysis.diagnosis import (
    ACTION_PRIORITY_ORDER,
    _apply_diagnosis_row_priorities,
    _build_diagnosis_content_summary,
    _chat_mention_counts,
    _competitor_breakdown_rows,
    _competitor_ids,
    _distinct_competitor_domains_with_link,
    _distinct_competitors_with_signal,
    _merged_diagnosis_gap_metrics,
    _platforms_with_gap,
    _total_domain_link_count,
    _total_mention_count,
    diagnosis_issue_type,
    diagnosis_mention_rate,
    gap_action_priority,
    has_diagnosis_content_gap,
    mention_action_priority,
)
from aperix_geo.services.analysis.entity import list_analysis_entities, own_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow


def _prompt_snapshots(
    *,
    entity_signals: list[LLMResponseSignalRow],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
    focus_entity_id: str,
    prompts: dict[UUID, Prompt],
) -> dict[UUID, dict[str, Any]]:
    by_prompt: dict[UUID, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in entity_signals:
        by_prompt[row.prompt_id].append(row)

    snapshots: dict[UUID, dict[str, Any]] = {}
    for prompt_id, subset in by_prompt.items():
        if prompt_id not in prompts:
            continue
        metrics = metrics_from_signals(
            subset,
            subject=subject,
            all_signals_for_voice=all_signals,
        )
        mention_own = sum(1 for row in subset if row.mentioned)
        mention_total = metrics.response_count
        mention_rate = diagnosis_mention_rate(
            mention_own_count=mention_own,
            mention_total_count=mention_total,
            visibility_rate=metrics.visibility_rate,
        )
        snapshots[prompt_id] = {
            "mention_rate": mention_rate,
            "mention_own_count": mention_own,
            "mention_total_count": mention_total,
            "average_rank": metrics.average_rank,
            "mention_issue_type": diagnosis_issue_type(mention_rate, metrics.average_rank),
            "mention_priority": mention_action_priority(mention_rate, metrics.average_rank),
        }
    return snapshots


def _load_items(
    db: Session,
    *,
    subject: Subject,
    signals: list[LLMResponseSignalRow],
) -> tuple[dict[UUID, dict[str, Any]], list[dict[str, Any]]]:
    entity = own_entity(subject)
    entity_signals = [row for row in signals if row.entity_id == entity.id]
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    prompt_snapshots = _prompt_snapshots(
        entity_signals=entity_signals,
        all_signals=signals,
        subject=subject,
        focus_entity_id=entity.id,
        prompts=prompts,
    )

    by_prompt: dict[UUID, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in entity_signals:
        by_prompt[row.prompt_id].append(row)

    items: list[dict[str, Any]] = []
    for prompt_id, prompt_entity_signals in by_prompt.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue

        response_ids = {row.response_id for row in prompt_entity_signals}
        snapshot = prompt_snapshots.get(prompt_id)
        if snapshot is None:
            continue

        gap = _merged_diagnosis_gap_metrics(
            focus_entity_id=entity.id,
            entity_signals=prompt_entity_signals,
            response_ids=response_ids,
            all_signals=signals,
            subject=subject,
        )
        if not has_diagnosis_content_gap(
            brand_gap_rate=gap["brand_gap_rate"],
            source_gap_rate=gap["source_gap_rate"],
            mention_priority=snapshot["mention_priority"],
        ):
            continue

        item = {
            "id": str(prompt_id),
            "prompt_id": str(prompt_id),
            "prompt_text": prompt.text,
            "platforms": gap["platforms"],
            "competitors": gap["competitors"],
            "brand_gap_rate": gap["brand_gap_rate"],
            "brand_gap_priority": gap["brand_gap_priority"],
            "source_gap_rate": gap["source_gap_rate"],
            "source_gap_priority": gap["source_gap_priority"],
            "brand_own_count": gap["brand_own_count"],
            "brand_total_count": gap["brand_total_count"],
            "source_own_count": gap["source_own_count"],
            "source_total_count": gap["source_total_count"],
        }
        item.update(
            {
                "mention_rate": snapshot["mention_rate"],
                "mention_own_count": snapshot["mention_own_count"],
                "mention_total_count": snapshot["mention_total_count"],
                "average_rank": snapshot["average_rank"],
                "mention_issue_type": snapshot["mention_issue_type"],
                "mention_priority": snapshot["mention_priority"],
            }
        )
        _apply_diagnosis_row_priorities(item)
        items.append(item)

    return prompt_snapshots, items


def _rank_key(row: dict[str, Any]) -> tuple[int, float, float, float]:
    return (
        ACTION_PRIORITY_ORDER.get(row["priority"], 9),
        row.get("mention_rate", 0),
        -row["brand_gap_rate"],
        -row["source_gap_rate"],
    )


def _sort_items(
    items: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if not sort_by:
        return sorted(items, key=_rank_key)

    reverse = order == "desc"
    if sort_by == "brand_gap_rate":
        return sorted(items, key=lambda row: row["brand_gap_rate"], reverse=reverse)
    if sort_by == "source_gap_rate":
        return sorted(items, key=lambda row: row["source_gap_rate"], reverse=reverse)
    if sort_by == "mention_rate":
        return sorted(items, key=lambda row: row.get("mention_rate", 0), reverse=reverse)
    if sort_by == "priority":
        return sorted(
            items,
            key=lambda row: ACTION_PRIORITY_ORDER.get(row.get("priority", "low"), 9),
            reverse=reverse,
        )
    return sorted(items, key=_rank_key, reverse=reverse)


def mem_diagnosis_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    signals: list[LLMResponseSignalRow],
    sort_by: str | None,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    _ = dt_from, dt_to
    _prompt_snapshots, items = _load_items(db, subject=subject, signals=signals)
    sorted_items = _sort_items(items, sort_by=sort_by, order=order)
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    start = (safe_page - 1) * safe_page_size
    return sorted_items[start : start + safe_page_size], len(sorted_items)


def mem_diagnosis_summary(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    signals: list[LLMResponseSignalRow],
) -> dict[str, Any]:
    _ = dt_from, dt_to
    prompt_snapshots, items = _load_items(db, subject=subject, signals=signals)
    return _build_diagnosis_content_summary(
        mention_snapshots=list(prompt_snapshots.values()),
        gap_items=items,
    )


def mem_diagnosis_detail(
    db: Session,
    *,
    subject: Subject,
    prompt: Prompt,
    dt_from: datetime,
    dt_to: datetime,
    signals: list[LLMResponseSignalRow],
) -> dict[str, Any]:
    _ = dt_from, dt_to
    entity = own_entity(subject)
    prompt_signals = [row for row in signals if row.prompt_id == prompt.id]
    all_signals = prompt_signals
    entity_signals = [row for row in prompt_signals if row.entity_id == entity.id]
    response_ids = {row.response_id for row in entity_signals}

    catalog_ids = {item.id for item in list_analysis_entities(subject)}
    entities = list_analysis_entities(subject)
    competitor_ids = _competitor_ids(entities, entity.id)
    domain_key_by_entity = {
        item.id: (item.domain or item.label).strip().lower()
        for item in entities
        if item.id in competitor_ids
    }

    gap_metrics = _merged_diagnosis_gap_metrics(
        focus_entity_id=entity.id,
        entity_signals=entity_signals,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
    )
    brand_gap_rate = gap_metrics["brand_gap_rate"]
    source_gap_rate = gap_metrics["source_gap_rate"]
    chat_mention_own, chat_mention_total = _chat_mention_counts(entity_signals, response_ids)

    brand_gap_platforms = _platforms_with_gap(
        focus_entity_id=entity.id,
        entity_signals=entity_signals,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
        metric="brand",
    )
    source_gap_platforms = _platforms_with_gap(
        focus_entity_id=entity.id,
        entity_signals=entity_signals,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
        metric="source",
    )

    return {
        "prompt_id": str(prompt.id),
        "prompt_text": prompt.text,
        "brand": {
            "gap_rate": brand_gap_rate,
            "gap_priority": gap_action_priority(brand_gap_rate),
            "chat_mention_own": chat_mention_own,
            "chat_mention_total": chat_mention_total,
            "competitor_brand_count": _distinct_competitors_with_signal(
                all_signals,
                response_ids=response_ids,
                competitor_ids=competitor_ids,
                signal_present=lambda row: row.mentioned,
            ),
            "total_mention_count": _total_mention_count(
                all_signals,
                response_ids=response_ids,
                catalog_ids=catalog_ids,
            ),
            "rows": _competitor_breakdown_rows(
                db,
                all_signals,
                subject=subject,
                focus_entity_id=entity.id,
                response_ids=response_ids,
                gap_platforms=brand_gap_platforms,
                metric="brand",
            ),
        },
        "source": {
            "gap_rate": source_gap_rate,
            "gap_priority": gap_action_priority(source_gap_rate),
            "chat_source_own": gap_metrics["source_own_count"],
            "chat_source_total": gap_metrics["source_total_count"],
            "competitor_source_count": _distinct_competitor_domains_with_link(
                all_signals,
                response_ids=response_ids,
                competitor_ids=competitor_ids,
                domain_key_by_entity=domain_key_by_entity,
            ),
            "total_source_count": _total_domain_link_count(
                all_signals,
                response_ids=response_ids,
                catalog_ids=catalog_ids,
            ),
            "rows": _competitor_breakdown_rows(
                db,
                all_signals,
                subject=subject,
                focus_entity_id=entity.id,
                response_ids=response_ids,
                gap_platforms=source_gap_platforms,
                metric="source",
            ),
        },
    }
