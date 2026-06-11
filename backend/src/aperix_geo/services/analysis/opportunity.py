"""Content and backlink opportunity analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Competitor, Prompt, Subject
from aperix_geo.services.analysis.aggregate import metrics_from_signals, other_mentioned_entity_labels
from aperix_geo.services.analysis.entity import own_entity, resolve_analysis_entity
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow, load_llm_response_signals
from aperix_geo.utils.url import host_matches_root, normalize_domain


def opportunity_priority(brand_gap: float, source_gap: float) -> str:
    peak = max(brand_gap, source_gap)
    if peak >= 0.8:
        return "high"
    if peak >= 0.5:
        return "medium"
    return "low"


def build_content_opportunities(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """按提示词 × 平台聚合内容机会：品牌提及差距与引用差距。"""
    entity = resolve_analysis_entity(subject, entity_id)
    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
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

        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        total = metrics.response_count
        if total == 0:
            continue

        brand_own = sum(1 for row in subset if row.mentioned)
        brand_gap = round(1 - brand_own / total, 4)
        source_own = sum(1 for row in subset if row.cited_on_source)
        source_gap = round(1 - source_own / total, 4)

        if brand_gap <= 0 and source_gap <= 0:
            continue

        response_ids = {row.response_id for row in subset}
        competitors = other_mentioned_entity_labels(
            response_ids,
            all_signals=all_signals,
            exclude_entity_id=entity.id,
            subject=subject,
        )

        items.append(
            {
                "id": f"{prompt_id}:{platform}",
                "prompt_id": str(prompt_id),
                "prompt_text": prompt.text,
                "platform": platform,
                "priority": opportunity_priority(brand_gap, source_gap),
                "competitors": competitors,
                "brand_gap_rate": brand_gap,
                "brand_own_count": brand_own,
                "brand_total_count": total,
                "source_gap_rate": source_gap,
                "source_own_count": source_own,
                "source_total_count": total,
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(
        key=lambda row: (
            priority_order.get(row["priority"], 9),
            -row["brand_gap_rate"],
            -row["source_gap_rate"],
        )
    )
    return {"entity_id": entity.id, "entity_label": entity.label, "items": items}


def citation_root_for_subject(subject: Subject) -> str | None:
    from aperix_geo.services.sampling.citation import citation_root

    return citation_root(subject)


def enterprise_domain_roots(db: Session, subject: Subject) -> set[str]:
    roots: set[str] = set()
    own_root = citation_root_for_subject(subject)
    if own_root:
        roots.add(own_root)
    if subject.domain:
        root = normalize_domain(subject.domain)
        if root:
            roots.add(root)
    for domain in db.execute(
        select(Competitor.domain).where(
            Competitor.subject_id == subject.id,
            Competitor.domain != "",
        )
    ).scalars():
        root = normalize_domain(domain)
        if root:
            roots.add(root)
    return roots


def classify_backlink_domain_type(host: str, enterprise_roots: set[str]) -> str:
    for root in enterprise_roots:
        if host_matches_root(host, root):
            return "enterprise"
    return "other"


def backlink_priority(prompt_count: int, chat_count: int) -> str:
    if prompt_count >= 5 or chat_count >= 8:
        return "high"
    if prompt_count >= 2 or chat_count >= 3:
        return "medium"
    return "low"


def build_backlink_opportunities(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    """按域名 × 平台聚合反向链接机会：未引用自有域名的回复中被 AI 引用的外部信源。"""
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    own_root = citation_root_for_subject(subject)
    enterprise_roots = enterprise_domain_roots(db, subject)
    own = own_entity(subject)
    own_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        entity_id=own.id,
    )
    cited_response_ids = {row.response_id for row in own_signals if row.cited_on_source}

    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"chat_count": 0, "prompt_ids": set()}
    )

    for row in rows:
        if row.id in cited_response_ids:
            continue

        parsed = row.parsed or {}
        hosts = {str(h).lower() for h in (parsed.get("url_hosts") or []) if h}
        for host in hosts:
            if own_root and host_matches_root(host, own_root):
                continue
            bucket = grouped[(host, row.platform)]
            bucket["chat_count"] += 1
            bucket["prompt_ids"].add(row.prompt_id)

    items: list[dict[str, Any]] = []
    for (host, platform), data in grouped.items():
        chat_count = data["chat_count"]
        prompt_count = len(data["prompt_ids"])
        if chat_count == 0:
            continue

        items.append(
            {
                "id": f"{host}:{platform}",
                "host": host,
                "platform": platform,
                "priority": backlink_priority(prompt_count, chat_count),
                "domain_type": classify_backlink_domain_type(host, enterprise_roots),
                "prompt_count": prompt_count,
                "chat_count": chat_count,
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(
        key=lambda row: (
            priority_order.get(row["priority"], 9),
            -row["chat_count"],
            -row["prompt_count"],
            row["host"],
        )
    )
    return {"items": items}
