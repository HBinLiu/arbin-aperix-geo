"""Aggregate citation counts across LLM responses in a time window."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, LLMResponse, Prompt, Subject, Topic
from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names
from aperix_geo.services.subject.labels import competitor_rank_label
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.text import mode_nonempty
from aperix_geo.utils.url import filter_citation_urls, hostname_from_url, is_placeholder_citation_host


def _competitor_domain_map(subject: Subject | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if subject is None:
        return mapping
    for competitor in subject.competitors or []:
        brand = (competitor.brand or "").strip()
        domain = (competitor.domain or "").strip()
        label = competitor_rank_label(brand=brand, domain=domain)
        if label and domain:
            mapping[label] = registrable_domain(domain) or domain
        if brand:
            mapping[brand] = registrable_domain(domain) or domain
    return mapping


def _aggregate_domains_from_parsed(rows: list[LLMResponse]) -> dict[str, int]:
    host_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for h in (r.parsed or {}).get("url_hosts") or []:
            if h and not is_placeholder_citation_host(str(h)):
                host_counts[str(h)] += 1
    return dict(host_counts)


def _aggregate_urls_from_parsed(rows: list[LLMResponse]) -> dict[str, int]:
    url_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for url in filter_citation_urls(list((r.parsed or {}).get("urls") or [])):
            if url:
                url_counts[str(url)] += 1
    return dict(url_counts)


def _load_prompt_topic_maps(
    db: Session,
    prompt_ids: set[UUID],
) -> tuple[dict[UUID, Prompt], dict[UUID, str]]:
    if not prompt_ids:
        return {}, {}
    prompts = db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids))).scalars().all()
    topic_ids = {prompt.topic_id for prompt in prompts}
    topics = (
        db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
        if topic_ids
        else []
    )
    topic_names = {topic.id: topic.name for topic in topics}
    return {prompt.id: prompt for prompt in prompts}, topic_names


def _citing_prompts_for_records(
    records: list[CitationUrl],
    *,
    prompt_map: dict[UUID, Prompt],
    topic_names: dict[UUID, str],
) -> list[dict[str, str]]:
    seen: set[UUID] = set()
    items: list[dict[str, str]] = []
    for record in records:
        prompt_id = record.prompt_id
        if prompt_id in seen:
            continue
        seen.add(prompt_id)
        prompt = prompt_map.get(prompt_id)
        if prompt is None:
            continue
        items.append(
            {
                "prompt_text": prompt.text,
                "topic_name": topic_names.get(prompt.topic_id, "未知主题"),
            }
        )
    return items


def _citing_prompts_for_url(
    url: str,
    rows: list[LLMResponse],
    *,
    prompt_map: dict[UUID, Prompt],
    topic_names: dict[UUID, str],
) -> list[dict[str, str]]:
    seen: set[UUID] = set()
    items: list[dict[str, str]] = []
    for row in rows:
        urls = filter_citation_urls(list((row.parsed or {}).get("urls") or []))
        if url not in urls:
            continue
        prompt_id = row.prompt_id
        if prompt_id in seen:
            continue
        seen.add(prompt_id)
        prompt = prompt_map.get(prompt_id)
        if prompt is None:
            continue
        items.append(
            {
                "prompt_text": prompt.text,
                "topic_name": topic_names.get(prompt.topic_id, "未知主题"),
            }
        )
    return items


def _mentioned_brands_for_records(
    records: list[CitationUrl],
    *,
    competitor_domains: dict[str, str],
) -> list[dict[str, str | None]]:
    labels: list[str] = []
    seen: set[str] = set()
    for record in records:
        for name in page_mentioned_brand_names(record.llm_analysis if isinstance(record.llm_analysis, dict) else {}):
            if name in seen:
                continue
            seen.add(name)
            labels.append(name)
    return [{"label": label, "domain": competitor_domains.get(label)} for label in labels]


def _aggregate_url_row(
    url: str,
    records: list[CitationUrl],
    *,
    total: int,
    competitor_domains: dict[str, str],
    prompt_map: dict[UUID, Prompt],
    topic_names: dict[UUID, str],
) -> dict[str, Any]:
    count = len(records)
    host = (hostname_from_url(url) or "").strip().lower()
    page_title = mode_nonempty([record.page_title for record in records])
    url_type = mode_nonempty([record.url_type for record in records])
    domain_type = mode_nonempty([record.domain_type for record in records])
    if not page_title:
        page_title = records[0].page_title if records else ""

    mentioned_brands = _mentioned_brands_for_records(records, competitor_domains=competitor_domains)
    has_brand_analysis = any(
        isinstance(record.llm_analysis, dict)
        and (
            "page_mentioned_brands" in record.llm_analysis
            or record.llm_analysis.get("analysis_source") in ("llm", "heuristic")
        )
        for record in records
    )

    return {
        "url": url,
        "host": host,
        "title": page_title or url,
        "url_type": url_type or None,
        "domain_type": domain_type or None,
        "count": count,
        "citation_rate": round(count / total, 4) if total else 0,
        "has_brand_analysis": has_brand_analysis,
        "mentioned_brands": mentioned_brands,
        "citing_prompts": _citing_prompts_for_records(
            records,
            prompt_map=prompt_map,
            topic_names=topic_names,
        ),
    }


def aggregate_citation_domains(
    db: Session,
    rows: list[LLMResponse],
) -> list[dict[str, Any]]:
    """Domain-level citation counts for a response window."""
    if not rows:
        return []
    total = len(rows)
    response_ids = [r.id for r in rows]
    stmt = (
        select(
            CitationDomain.domain,
            func.sum(CitationDomain.cite_count),
            func.max(CitationDomain.domain_type),
        )
        .where(CitationDomain.response_id.in_(response_ids))
        .group_by(CitationDomain.domain)
    )
    db_rows = db.execute(stmt).all()
    if db_rows:
        host_counts = {domain: int(count) for domain, count, _ in db_rows if domain}
        domain_types = {domain: str(domain_type or "").strip() for domain, _, domain_type in db_rows if domain}
    else:
        host_counts = _aggregate_domains_from_parsed(rows)
        domain_types = {}
    return sorted(
        [
            {
                "host": host,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
                "domain_type": domain_types.get(host) or None,
            }
            for host, count in host_counts.items()
        ],
        key=lambda row: -row["count"],
    )


def aggregate_citation_urls(
    db: Session,
    rows: list[LLMResponse],
    *,
    subject: Subject | None = None,
) -> list[dict[str, Any]]:
    """URL-level citation counts and source-page metadata for a response window."""
    if not rows:
        return []
    total = len(rows)
    response_ids = [r.id for r in rows]
    competitor_domains = _competitor_domain_map(subject)

    records = db.execute(
        select(CitationUrl).where(CitationUrl.response_id.in_(response_ids))
    ).scalars().all()

    grouped: dict[str, list[CitationUrl]] = defaultdict(list)
    for record in records:
        grouped[record.url].append(record)

    prompt_ids = {record.prompt_id for record in records} | {row.prompt_id for row in rows}
    prompt_map, topic_names = _load_prompt_topic_maps(db, prompt_ids)

    if grouped:
        return sorted(
            [
                _aggregate_url_row(
                    url,
                    grouped[url],
                    total=total,
                    competitor_domains=competitor_domains,
                    prompt_map=prompt_map,
                    topic_names=topic_names,
                )
                for url in grouped
            ],
            key=lambda row: -row["count"],
        )

    url_counts = _aggregate_urls_from_parsed(rows)
    return sorted(
        [
            {
                "url": url,
                "host": (hostname_from_url(url) or "").strip().lower(),
                "title": url.rsplit("/", 1)[-1] or url,
                "url_type": None,
                "domain_type": None,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
                "has_brand_analysis": False,
                "mentioned_brands": [],
                "citing_prompts": _citing_prompts_for_url(
                    url,
                    rows,
                    prompt_map=prompt_map,
                    topic_names=topic_names,
                ),
            }
            for url, count in url_counts.items()
        ],
        key=lambda row: -row["count"],
    )
