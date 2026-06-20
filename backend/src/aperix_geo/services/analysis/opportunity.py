"""Content and backlink opportunity analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, EntityKind, LLMResponse, LLMResponseSignal, LLMResponseStatus, Prompt, SamplingJob, Subject
from aperix_geo.services.analysis.entity import list_analysis_entities, own_entity
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals
from aperix_geo.services.sampling.citation.geo_classify import DOMAIN_TYPE_ENTERPRISE, DOMAIN_TYPE_OTHER
from aperix_geo.utils.url import host_matches_root, hostname_from_url, normalize_domain


def _has_domain_link_in_citations(row: LLMResponseSignalRow) -> bool:
    """Reply citation list contains a link to the entity's domain."""
    return row.has_domain_link


def competitive_gap_metrics(
    *,
    focus_entity_id: str,
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
) -> dict[str, Any]:
    """Relative gap vs configured competitors on the same reply pool."""
    total = len(response_ids)
    if total == 0:
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
    label_by_id = {entity.id: entity.label for entity in entities}
    catalog_order = {entity.label: index for index, entity in enumerate(entities)}

    focus_rows = [
        row
        for row in all_signals
        if row.response_id in response_ids and row.entity_id == focus_entity_id
    ]
    brand_own = sum(1 for row in focus_rows if row.mentioned)
    source_own = sum(1 for row in focus_rows if _has_domain_link_in_citations(row))
    own_brand_rate = brand_own / total
    own_source_rate = source_own / total

    best_brand_rate = 0.0
    best_source_rate = 0.0
    brand_leaders: list[str] = []
    source_leaders: list[str] = []

    for entity in entities:
        if entity.id == focus_entity_id:
            continue
        comp_rows = [
            row
            for row in all_signals
            if row.response_id in response_ids and row.entity_id == entity.id
        ]
        comp_brand_rate = sum(1 for row in comp_rows if row.mentioned) / total
        comp_source_rate = sum(1 for row in comp_rows if _has_domain_link_in_citations(row)) / total

        if comp_brand_rate > best_brand_rate:
            best_brand_rate = comp_brand_rate
            brand_leaders = [label_by_id[entity.id]]
        elif comp_brand_rate == best_brand_rate and comp_brand_rate > 0:
            brand_leaders.append(label_by_id[entity.id])

        if comp_source_rate > best_source_rate:
            best_source_rate = comp_source_rate
            source_leaders = [label_by_id[entity.id]]
        elif comp_source_rate == best_source_rate and comp_source_rate > 0:
            source_leaders.append(label_by_id[entity.id])

    competitors: list[str] = []
    seen: set[str] = set()
    for label in sorted(
        {*brand_leaders, *source_leaders},
        key=lambda item: catalog_order.get(item, 10_000),
    ):
        if label not in seen:
            seen.add(label)
            competitors.append(label)

    brand_gap_rate = round(max(0.0, best_brand_rate - own_brand_rate), 4)
    source_gap_rate = round(max(0.0, best_source_rate - own_source_rate), 4)

    return {
        "brand_gap_rate": brand_gap_rate,
        "brand_gap_priority": gap_priority(brand_gap_rate),
        "source_gap_rate": source_gap_rate,
        "source_gap_priority": gap_priority(source_gap_rate),
        "competitors": competitors,
        "brand_own_count": brand_own,
        "brand_total_count": total,
        "source_own_count": source_own,
        "source_total_count": total,
    }


def gap_priority(gap_rate: float) -> str:
    if gap_rate >= 0.8:
        return "high"
    if gap_rate >= 0.5:
        return "medium"
    return "low"


def opportunity_priority(brand_gap: float, source_gap: float) -> str:
    return gap_priority(max(brand_gap, source_gap))


_MAX_PAGE_SIZE = 100
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
    return safe_page, safe_page_size


def _paginate(items: list[Any], *, page: int, page_size: int) -> tuple[list[Any], int, int, int]:
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return items[start : start + safe_page_size], total, safe_page, safe_page_size


def _filter_content_by_search(items: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    query = (search or "").strip().lower()
    if not query:
        return items
    return [item for item in items if query in item["prompt_text"].lower()]


def _content_row_rank_key(row: dict[str, Any]) -> tuple[int, float, float]:
    """默认排序：优先级 → 品牌差距 → 来源差距（均为高/大者优先）。"""
    return (
        _PRIORITY_ORDER.get(row["priority"], 9),
        -row["brand_gap_rate"],
        -row["source_gap_rate"],
    )


def _sort_content_items(
    items: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if not sort_by:
        return sorted(items, key=_content_row_rank_key)

    reverse = order == "desc"

    if sort_by == "brand_gap_rate":
        return sorted(items, key=lambda row: row["brand_gap_rate"], reverse=reverse)
    if sort_by == "source_gap_rate":
        return sorted(items, key=lambda row: row["source_gap_rate"], reverse=reverse)

    return sorted(items, key=_content_row_rank_key, reverse=reverse)


def build_content_opportunities(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """按提示词 × 平台聚合内容机会：品牌提及差距与引用差距（始终以自有品牌为焦点）。"""
    entity = own_entity(subject)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    entity_signals = [row for row in all_signals if row.entity_id == entity.id]
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    grouped: dict[tuple[UUID, str], list[LLMResponseSignalRow]] = defaultdict(list)
    for row in entity_signals:
        grouped[(row.prompt_id, row.platform)].append(row)

    items: list[dict[str, Any]] = []
    for (prompt_id, platform), subset in grouped.items():
        prompt = prompts.get(prompt_id)
        if not prompt:
            continue

        response_ids = {row.response_id for row in subset}
        gap = competitive_gap_metrics(
            focus_entity_id=entity.id,
            response_ids=response_ids,
            all_signals=all_signals,
            subject=subject,
        )
        if gap["brand_gap_rate"] <= 0 and gap["source_gap_rate"] <= 0:
            continue

        items.append(
            {
                "id": f"{prompt_id}:{platform}",
                "prompt_id": str(prompt_id),
                "prompt_text": prompt.text,
                "platform": platform,
                "priority": opportunity_priority(gap["brand_gap_rate"], gap["source_gap_rate"]),
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
        )

    merged = _merge_content_opportunity_items(items)
    filtered = _filter_content_by_search(merged, search)
    sorted_items = _sort_content_items(filtered, sort_by=sort_by, order=order)
    page_items, total, safe_page, safe_page_size = _paginate(
        sorted_items,
        page=page,
        page_size=page_size,
    )
    return {
        "entity_id": entity.id,
        "entity_label": entity.label,
        "items": page_items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
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


def _merge_content_opportunity_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate prompt × platform rows into one row per prompt with platforms[]."""
    by_prompt: dict[str, dict[str, Any]] = {}

    for item in items:
        prompt_id = item["prompt_id"]
        existing = by_prompt.get(prompt_id)
        if existing is None:
            by_prompt[prompt_id] = {
                "id": prompt_id,
                "prompt_id": prompt_id,
                "prompt_text": item["prompt_text"],
                "platforms": [item["platform"]],
                "priority": item["priority"],
                "competitors": list(item["competitors"]),
                "brand_gap_rate": item["brand_gap_rate"],
                "brand_gap_priority": item["brand_gap_priority"],
                "source_gap_rate": item["source_gap_rate"],
                "source_gap_priority": item["source_gap_priority"],
                "brand_own_count": item["brand_own_count"],
                "brand_total_count": item["brand_total_count"],
                "source_own_count": item["source_own_count"],
                "source_total_count": item["source_total_count"],
            }
            continue

        if item["platform"] not in existing["platforms"]:
            existing["platforms"].append(item["platform"])

        _merge_gap_counts(
            existing,
            item,
            gap_key="brand_gap_rate",
            own_key="brand_own_count",
            total_key="brand_total_count",
        )
        _merge_gap_counts(
            existing,
            item,
            gap_key="source_gap_rate",
            own_key="source_own_count",
            total_key="source_total_count",
        )
        existing["brand_gap_priority"] = gap_priority(existing["brand_gap_rate"])
        existing["source_gap_priority"] = gap_priority(existing["source_gap_rate"])
        existing["priority"] = opportunity_priority(
            existing["brand_gap_rate"],
            existing["source_gap_rate"],
        )

        for label in item["competitors"]:
            if label not in existing["competitors"]:
                existing["competitors"].append(label)

    merged = list(by_prompt.values())
    return merged


def _merged_competitive_gap_metrics(
    *,
    focus_entity_id: str,
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
    all_signals: list[LLMResponseSignalRow],
    subject: Subject,
) -> dict[str, Any]:
    """Match list row merge: per-platform gap, then take max gap and its reply counts."""
    by_platform: dict[str, set[UUID]] = defaultdict(set)
    for row in entity_signals:
        if row.response_id in response_ids:
            by_platform[row.platform].add(row.response_id)

    if not by_platform:
        return {
            **competitive_gap_metrics(
                focus_entity_id=focus_entity_id,
                response_ids=set(),
                all_signals=all_signals,
                subject=subject,
            ),
            "platforms": [],
        }

    merged: dict[str, Any] | None = None
    for platform in sorted(by_platform.keys()):
        gap = competitive_gap_metrics(
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
        merged["brand_gap_priority"] = gap_priority(merged["brand_gap_rate"])
        merged["source_gap_priority"] = gap_priority(merged["source_gap_rate"])

    if merged is not None:
        return merged

    gap = competitive_gap_metrics(
        focus_entity_id=focus_entity_id,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
    )
    return {**gap, "platforms": sorted(by_platform.keys())}


def _response_ids_by_platform(
    entity_signals: list[LLMResponseSignalRow],
    response_ids: set[UUID],
) -> dict[str, set[UUID]]:
    by_platform: dict[str, set[UUID]] = defaultdict(set)
    for row in entity_signals:
        if row.response_id in response_ids:
            by_platform[row.platform].add(row.response_id)
    return by_platform


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
        if competitive_gap_metrics(
            focus_entity_id=focus_entity_id,
            response_ids=pool,
            all_signals=all_signals,
            subject=subject,
        )[gap_key]
        > 0
    }


def _scoped_response_ids(
    entity_signals: list[LLMResponseSignalRow],
    *,
    platforms: list[str] | None,
) -> set[UUID]:
    scoped = entity_signals
    if platforms:
        allowed = set(platforms)
        scoped = [row for row in scoped if row.platform in allowed]
    return {row.response_id for row in scoped}


def _competitor_entity_ids(catalog_ids: set[str], focus_entity_id: str) -> set[str]:
    return {entity_id for entity_id in catalog_ids if entity_id != focus_entity_id}


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
        and _has_domain_link_in_citations(row)
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
        if not _has_domain_link_in_citations(row):
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
        host = hostname_from_url(text)
        if host and host_matches_root(host, root):
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
    from aperix_geo.services.analysis.aggregate import metrics_from_signals

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
            linked_rows = sum(1 for row in subset if _has_domain_link_in_citations(row))
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
            elif any(_has_domain_link_in_citations(row) for row in platform_subset):
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
                row.response_id for row in subset if _has_domain_link_in_citations(row)
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


def build_content_opportunity_detail(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    prompt_id: UUID,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Single prompt content-opportunity drill-down: gap summary + competitor breakdown."""
    from fastapi import HTTPException, status

    entity = own_entity(subject)
    prompt = db.get(Prompt, prompt_id)
    if not prompt or prompt.subject_id != subject.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    entity_signals = [row for row in all_signals if row.entity_id == entity.id]
    response_ids = _scoped_response_ids(entity_signals, platforms=platforms)
    if not response_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses for prompt")

    catalog_ids = {item.id for item in list_analysis_entities(subject)}
    competitor_ids = _competitor_entity_ids(catalog_ids, entity.id)
    entities = list_analysis_entities(subject)
    domain_key_by_entity = {
        item.id: (item.domain or item.label).strip().lower()
        for item in entities
        if item.id in competitor_ids
    }

    gap_metrics = _merged_competitive_gap_metrics(
        focus_entity_id=entity.id,
        entity_signals=entity_signals,
        response_ids=response_ids,
        all_signals=all_signals,
        subject=subject,
    )
    brand_gap_rate = gap_metrics["brand_gap_rate"]
    source_gap_rate = gap_metrics["source_gap_rate"]
    chat_mention_own = gap_metrics["brand_own_count"]
    chat_mention_total = gap_metrics["brand_total_count"]
    chat_source_own = gap_metrics["source_own_count"]
    chat_source_total = gap_metrics["source_total_count"]
    active_platforms = gap_metrics["platforms"]
    competitor_brand_count = _distinct_competitors_with_signal(
        all_signals,
        response_ids=response_ids,
        competitor_ids=competitor_ids,
        signal_present=lambda row: row.mentioned,
    )
    competitor_source_count = _distinct_competitor_domains_with_link(
        all_signals,
        response_ids=response_ids,
        competitor_ids=competitor_ids,
        domain_key_by_entity=domain_key_by_entity,
    )
    total_mention_count = _total_mention_count(
        all_signals,
        response_ids=response_ids,
        catalog_ids=catalog_ids,
    )
    total_source_count = _total_domain_link_count(
        all_signals,
        response_ids=response_ids,
        catalog_ids=catalog_ids,
    )

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

    brand_rows = _competitor_breakdown_rows(
        db,
        all_signals,
        subject=subject,
        focus_entity_id=entity.id,
        response_ids=response_ids,
        gap_platforms=brand_gap_platforms,
        metric="brand",
    )
    source_rows = _competitor_breakdown_rows(
        db,
        all_signals,
        subject=subject,
        focus_entity_id=entity.id,
        response_ids=response_ids,
        gap_platforms=source_gap_platforms,
        metric="source",
    )

    return {
        "prompt_id": str(prompt_id),
        "prompt_text": prompt.text,
        "entity_id": entity.id,
        "entity_label": entity.label,
        "platforms": platforms or active_platforms or sorted(
            {row.platform for row in entity_signals if row.response_id in response_ids}
        ),
        "brand": {
            "gap_rate": brand_gap_rate,
            "gap_priority": gap_priority(brand_gap_rate),
            "chat_mention_own": chat_mention_own,
            "chat_mention_total": chat_mention_total,
            "competitor_brand_count": competitor_brand_count,
            "total_mention_count": total_mention_count,
            "rows": brand_rows,
        },
        "source": {
            "gap_rate": source_gap_rate,
            "gap_priority": gap_priority(source_gap_rate),
            "chat_source_own": chat_source_own,
            "chat_source_total": chat_source_total,
            "competitor_source_count": competitor_source_count,
            "total_source_count": total_source_count,
            "rows": source_rows,
        },
    }


def citation_root_for_subject(subject: Subject) -> str | None:
    from aperix_geo.services.sampling.citation import citation_root

    return citation_root(subject)


def enterprise_domain_roots(subject: Subject) -> set[str]:
    roots: set[str] = set()
    own_root = citation_root_for_subject(subject)
    if own_root:
        roots.add(own_root)
    if subject.domain:
        root = normalize_domain(subject.domain)
        if root:
            roots.add(root)
    for competitor in subject.competitors or []:
        if not competitor.domain:
            continue
        root = normalize_domain(competitor.domain)
        if root:
            roots.add(root)
    return roots


def _fallback_domain_type(host: str, enterprise_roots: set[str]) -> str:
    for root in enterprise_roots:
        if host_matches_root(host, root):
            return DOMAIN_TYPE_ENTERPRISE
    return DOMAIN_TYPE_OTHER


def _lookup_citation_domain_types(
    db: Session,
    *,
    response_ids: list[UUID],
    hosts: set[str],
) -> dict[str, str]:
    if not response_ids or not hosts:
        return {}
    execute = getattr(db, "execute", None)
    if execute is None:
        return {}
    rows = execute(
        select(
            CitationDomain.domain,
            func.max(CitationDomain.domain_type),
        )
        .where(
            CitationDomain.response_id.in_(response_ids),
            CitationDomain.domain.in_(hosts),
        )
        .group_by(CitationDomain.domain)
    ).all()
    return {
        str(domain).strip().lower(): str(domain_type or "").strip()
        for domain, domain_type in rows
        if domain and str(domain_type or "").strip()
    }


def backlink_priority(prompt_count: int, chat_count: int) -> str:
    if prompt_count >= 5 or chat_count >= 8:
        return "high"
    if prompt_count >= 2 or chat_count >= 3:
        return "medium"
    return "low"


_BACKLINK_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _backlink_row_rank_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        _BACKLINK_PRIORITY_ORDER.get(row["priority"], 9),
        -row["chat_count"],
        -row["prompt_count"],
        row["host"],
    )


def _filter_backlink_by_search(items: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    query = (search or "").strip().lower()
    if not query:
        return items
    return [item for item in items if query in item["host"].lower()]


def _sort_backlink_items(
    items: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if not sort_by:
        return sorted(items, key=_backlink_row_rank_key)

    reverse = order == "desc"
    if sort_by == "priority":
        return sorted(
            items,
            key=lambda row: (_BACKLINK_PRIORITY_ORDER.get(row["priority"], 9), row["host"]),
            reverse=reverse,
        )
    if sort_by == "prompt_count":
        return sorted(items, key=lambda row: row["prompt_count"], reverse=reverse)
    if sort_by == "chat_count":
        return sorted(items, key=lambda row: row["chat_count"], reverse=reverse)
    if sort_by == "citation_count":
        return sorted(items, key=lambda row: row["citation_count"], reverse=reverse)
    return sorted(items, key=_backlink_row_rank_key)


@dataclass(frozen=True)
class _BacklinkResponseRow:
    response_id: UUID
    platform: str
    prompt_id: UUID
    parsed: dict[str, Any]
    own_cited_on_source: bool


class _BacklinkResponseLoader:
    """Patchable loader (tests assign to `.override`)."""

    override: Callable[..., list[_BacklinkResponseRow]] | None = None

    def __call__(
        self,
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    ) -> list[_BacklinkResponseRow]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
        return self._load(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        )

    @staticmethod
    def _load(
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> list[_BacklinkResponseRow]:
        own_kind = EntityKind.own.value
        stmt = (
            select(
                LLMResponse.id,
                LLMResponse.platform,
                LLMResponse.prompt_id,
                LLMResponse.parsed,
                LLMResponseSignal.cited_on_source,
            )
            .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
            .outerjoin(
                LLMResponseSignal,
                and_(
                    LLMResponseSignal.response_id == LLMResponse.id,
                    LLMResponseSignal.subject_id == subject.id,
                    LLMResponseSignal.entity_kind == own_kind,
                ),
            )
            .where(
                SamplingJob.subject_id == subject.id,
                LLMResponse.created_at >= dt_from,
                LLMResponse.created_at <= dt_to,
                LLMResponse.status == LLMResponseStatus.success,
            )
        )
        if platform:
            stmt = stmt.where(LLMResponse.platform.in_(platform))
        if topic_id:
            stmt = stmt.join(Prompt, LLMResponse.prompt_id == Prompt.id).where(
                Prompt.topic_id.in_(topic_id)
            )

        rows: list[_BacklinkResponseRow] = []
        for response_id, platform_value, prompt_id, parsed, cited_on_source in db.execute(stmt).all():
            rows.append(
                _BacklinkResponseRow(
                    response_id=response_id,
                    platform=platform_value,
                    prompt_id=prompt_id,
                    parsed=parsed or {},
                    own_cited_on_source=bool(cited_on_source),
                )
            )
        return rows


_load_backlink_responses = _BacklinkResponseLoader()


def _aggregate_backlink_items(
    response_rows: list[_BacklinkResponseRow],
    *,
    subject: Subject,
    db: Session,
) -> list[dict[str, Any]]:
    own_root = citation_root_for_subject(subject)
    enterprise_roots = enterprise_domain_roots(subject)
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"chat_count": 0, "citation_count": 0, "prompt_ids": set(), "platforms": set()}
    )

    for row in response_rows:
        if row.own_cited_on_source:
            continue
        seen_hosts_in_row: set[str] = set()
        for raw_host in row.parsed.get("url_hosts") or []:
            host = str(raw_host).lower()
            if not host:
                continue
            if own_root and host_matches_root(host, own_root):
                continue
            bucket = grouped[host]
            bucket["citation_count"] += 1
            if host in seen_hosts_in_row:
                continue
            seen_hosts_in_row.add(host)
            bucket["chat_count"] += 1
            bucket["prompt_ids"].add(row.prompt_id)
            bucket["platforms"].add(row.platform)

    domain_types = _lookup_citation_domain_types(
        db,
        response_ids=[row.response_id for row in response_rows],
        hosts=set(grouped.keys()),
    )

    items: list[dict[str, Any]] = []
    for host, data in grouped.items():
        chat_count = data["chat_count"]
        prompt_count = len(data["prompt_ids"])
        if chat_count == 0:
            continue
        items.append(
            {
                "id": host,
                "host": host,
                "platforms": sorted(data["platforms"]),
                "priority": backlink_priority(prompt_count, chat_count),
                "domain_type": domain_types.get(host) or _fallback_domain_type(host, enterprise_roots),
                "citation_count": data["citation_count"],
                "prompt_count": prompt_count,
                "chat_count": chat_count,
            }
        )
    return items


def build_backlink_opportunities(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Aggregate external citation hosts where own brand is not cited on source."""
    response_rows = _load_backlink_responses(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    items = _aggregate_backlink_items(response_rows, subject=subject, db=db)
    filtered = _filter_backlink_by_search(items, search)
    sorted_items = _sort_backlink_items(filtered, sort_by=sort_by, order=order)
    page_items, total, safe_page, safe_page_size = _paginate(
        sorted_items,
        page=page,
        page_size=page_size,
    )
    return {
        "items": page_items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


@dataclass(frozen=True)
class _BacklinkHostContext:
    host: str
    response_ids: frozenset[UUID]
    citation_count: int
    chat_count: int
    prompt_ids: frozenset[UUID]
    platforms: list[str]


def _backlink_host_context(
    response_rows: list[_BacklinkResponseRow],
    *,
    host: str,
    subject: Subject,
) -> _BacklinkHostContext | None:
    host = (host or "").strip().lower()
    if not host:
        return None
    own_root = citation_root_for_subject(subject)
    citation_count = 0
    chat_count = 0
    prompt_ids: set[UUID] = set()
    platforms: set[str] = set()
    response_ids: set[UUID] = set()

    for row in response_rows:
        if row.own_cited_on_source:
            continue
        seen_in_row = False
        for raw_host in row.parsed.get("url_hosts") or []:
            h = str(raw_host).lower()
            if not h or h != host:
                continue
            if own_root and host_matches_root(h, own_root):
                continue
            citation_count += 1
            if seen_in_row:
                continue
            seen_in_row = True
            chat_count += 1
            response_ids.add(row.response_id)
            prompt_ids.add(row.prompt_id)
            platforms.add(row.platform)

    if chat_count == 0:
        return None

    return _BacklinkHostContext(
        host=host,
        response_ids=frozenset(response_ids),
        citation_count=citation_count,
        chat_count=chat_count,
        prompt_ids=frozenset(prompt_ids),
        platforms=sorted(platforms),
    )


def _backlink_mentioned_competitors(
    db: Session,
    *,
    subject: Subject,
    response_ids: frozenset[UUID],
    host: str,
) -> list[dict[str, str | None]]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _competitor_domain_map,
        _url_matches_host,
    )
    from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names

    if not response_ids:
        return []

    own = own_entity(subject)
    own_keys = {own.label.lower()}
    if subject.brand:
        own_keys.add(subject.brand.strip().lower())

    records = db.execute(
        select(CitationUrl).where(
            CitationUrl.response_id.in_(list(response_ids)),
            _url_matches_host(CitationUrl.url, host),
        )
    ).scalars().all()
    competitor_domains = _competitor_domain_map(subject)
    seen: set[str] = set()
    items: list[dict[str, str | None]] = []
    for record in records:
        analysis = record.llm_analysis if isinstance(record.llm_analysis, dict) else {}
        for name in page_mentioned_brand_names(analysis):
            key = name.lower()
            if key in own_keys or key in seen:
                continue
            seen.add(key)
            items.append({"label": name, "domain": competitor_domains.get(name)})
    return items


def _empty_backlink_detail(host: str) -> dict[str, Any]:
    return {
        "host": host,
        "domain_type": None,
        "priority": "low",
        "platforms": [],
        "citation_count": 0,
        "citation_rate": 0,
        "chat_count": 0,
        "prompt_count": 0,
        "mentioned_competitors": [],
    }


def build_backlink_opportunity_detail(
    db: Session,
    *,
    subject: Subject,
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    host = (host or "").strip().lower()
    response_rows = _load_backlink_responses(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    ctx = _backlink_host_context(response_rows, host=host, subject=subject)
    if ctx is None:
        return _empty_backlink_detail(host)

    domain_types = _lookup_citation_domain_types(
        db,
        response_ids=list(ctx.response_ids),
        hosts={host},
    )
    enterprise_roots = enterprise_domain_roots(subject)
    domain_type = domain_types.get(host) or _fallback_domain_type(host, enterprise_roots)
    prompt_count = len(ctx.prompt_ids)

    from aperix_geo.services.analysis._query import count_responses_in_window

    response_total = count_responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )

    return {
        "host": host,
        "domain_type": domain_type,
        "priority": backlink_priority(prompt_count, ctx.chat_count),
        "platforms": ctx.platforms,
        "citation_count": ctx.citation_count,
        "citation_rate": round(ctx.chat_count / response_total, 4) if response_total else 0,
        "chat_count": ctx.chat_count,
        "prompt_count": prompt_count,
        "mentioned_competitors": _backlink_mentioned_competitors(
            db,
            subject=subject,
            response_ids=ctx.response_ids,
            host=host,
        ),
    }


def build_backlink_opportunity_urls_page(
    db: Session,
    *,
    subject: Subject,
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _aggregate_url_row,
        _competitor_domain_map,
        _load_prompt_topic_maps,
        _normalize_pagination,
        _url_matches_host,
    )

    host = (host or "").strip().lower()
    response_rows = _load_backlink_responses(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    ctx = _backlink_host_context(response_rows, host=host, subject=subject)
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_ids = list(ctx.response_ids)
    response_total = ctx.chat_count
    count_expr = func.count(CitationUrl.id)
    grouped = (
        select(
            CitationUrl.url.label("url"),
            count_expr.label("count"),
        )
        .where(
            CitationUrl.response_id.in_(response_ids),
            _url_matches_host(CitationUrl.url, host),
        )
        .group_by(CitationUrl.url)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    order_clause = grouped.c.count.asc() if order == "asc" else grouped.c.count.desc()
    offset = (safe_page - 1) * safe_page_size
    page_rows = db.execute(
        select(grouped.c.url, grouped.c.count)
        .order_by(order_clause, grouped.c.url.asc())
        .offset(offset)
        .limit(safe_page_size)
    ).all()
    _ = sort_by

    page_urls = [str(url) for url, _count in page_rows if url]
    if not page_urls:
        return {
            "items": [],
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": response_total,
        }

    joined = db.execute(
        select(CitationUrl, LLMResponse.platform)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(
            CitationUrl.url.in_(page_urls),
            CitationUrl.response_id.in_(response_ids),
        )
    ).all()

    grouped_records: dict[str, list[CitationUrl]] = defaultdict(list)
    platforms_by_url: dict[str, set[str]] = defaultdict(set)
    for record, platform_value in joined:
        grouped_records[record.url].append(record)
        if platform_value:
            platforms_by_url[record.url].add(str(platform_value))

    prompt_ids = {record.prompt_id for record, _platform in joined}
    prompt_map, topic_names = _load_prompt_topic_maps(db, prompt_ids)
    competitor_domains = _competitor_domain_map(subject)

    items = []
    for url in page_urls:
        row = _aggregate_url_row(
            url,
            grouped_records.get(url, []),
            total=response_total,
            competitor_domains=competitor_domains,
            prompt_map=prompt_map,
            topic_names=topic_names,
        )
        row["platforms"] = sorted(platforms_by_url.get(url, set()))
        items.append(row)

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }


def build_backlink_opportunity_prompts_page(
    db: Session,
    *,
    subject: Subject,
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import _normalize_pagination, _url_matches_host

    host = (host or "").strip().lower()
    response_rows = _load_backlink_responses(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    ctx = _backlink_host_context(response_rows, host=host, subject=subject)
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_ids = list(ctx.response_ids)
    response_total = ctx.chat_count
    count_expr = func.count(CitationUrl.id)
    grouped = (
        select(
            CitationUrl.prompt_id.label("prompt_id"),
            count_expr.label("count"),
        )
        .where(
            CitationUrl.response_id.in_(response_ids),
            _url_matches_host(CitationUrl.url, host),
        )
        .group_by(CitationUrl.prompt_id)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    order_clause = grouped.c.count.asc() if order == "asc" else grouped.c.count.desc()
    offset = (safe_page - 1) * safe_page_size
    page_rows = db.execute(
        select(grouped.c.prompt_id, grouped.c.count)
        .order_by(order_clause, grouped.c.prompt_id.asc())
        .offset(offset)
        .limit(safe_page_size)
    ).all()
    _ = sort_by

    page_prompt_ids = [prompt_id for prompt_id, _count in page_rows if prompt_id is not None]
    if not page_prompt_ids:
        return {
            "items": [],
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": response_total,
        }

    prompts = db.execute(select(Prompt).where(Prompt.id.in_(page_prompt_ids))).scalars().all()
    prompt_map = {prompt.id: prompt for prompt in prompts}
    topic_ids = {prompt.topic_id for prompt in prompts}
    from aperix_geo.db.models import Topic

    topics = (
        db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
        if topic_ids
        else []
    )
    topic_names = {str(topic.id): topic.name for topic in topics}
    count_by_prompt = {prompt_id: int(count) for prompt_id, count in page_rows}

    platform_rows = db.execute(
        select(CitationUrl.prompt_id, LLMResponse.platform)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(
            CitationUrl.response_id.in_(response_ids),
            CitationUrl.prompt_id.in_(page_prompt_ids),
            _url_matches_host(CitationUrl.url, host),
        )
        .distinct()
    ).all()
    platforms_by_prompt: dict[UUID, set[str]] = defaultdict(set)
    for prompt_id, platform_value in platform_rows:
        if prompt_id is not None and platform_value:
            platforms_by_prompt[prompt_id].add(str(platform_value))

    items = [
        {
            "id": str(prompt_id),
            "name": (prompt_map.get(prompt_id) and prompt_map[prompt_id].text) or "未知提示词",
            "topic_name": topic_names.get(
                str(prompt_map[prompt_id].topic_id) if prompt_id in prompt_map else "",
                "未知主题",
            ),
            "platforms": sorted(platforms_by_prompt.get(prompt_id, set())),
            "count": count_by_prompt.get(prompt_id, 0),
            "citation_rate": round(count_by_prompt.get(prompt_id, 0) / response_total, 4)
            if response_total
            else 0,
        }
        for prompt_id in page_prompt_ids
    ]
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }
