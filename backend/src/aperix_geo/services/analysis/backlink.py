"""Backlink opportunity page builders."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, LLMResponse, Prompt, Subject, Topic
from aperix_geo.services.analysis.backlink_sql import (
    _attach_backlink_platforms,
    _backlink_domain_filter,
    _backlink_domain_response_ids_stmt,
    _backlink_window_subquery,
    _query_backlink_domain_context,
    _query_backlink_domain_page,
    backlink_priority,
)
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.utils.net import citation_registrable_key


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
    """Aggregate external citation domains where own brand is not cited on source."""
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    page_items, total = _query_backlink_domain_page(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        search=search,
        sort_by=sort_by,
        order=order,
        page=safe_page,
        page_size=safe_page_size,
    )
    if page_items and _query_backlink_domain_page.override is None:
        _attach_backlink_platforms(
            db,
            items=page_items,
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        )
    return {
        "items": page_items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def _backlink_mentioned_competitors(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> list[dict[str, str | None]]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _competitor_domain_map,
        _url_matches_registrable,
    )
    from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names

    response_ids_stmt = _backlink_domain_response_ids_stmt(
        subject_id=subject_id,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )

    own = own_entity(subject)
    own_keys = {own.label.lower()}
    if subject.brand:
        own_keys.add(subject.brand.strip().lower())

    records = db.execute(
        select(CitationUrl.llm_analysis).where(
            CitationUrl.response_id.in_(response_ids_stmt),
            _url_matches_registrable(CitationUrl.url, domain),
        )
    ).scalars().all()
    competitor_domains = _competitor_domain_map(subject)
    seen: set[str] = set()
    items: list[dict[str, str | None]] = []
    for analysis in records:
        if not isinstance(analysis, dict):
            continue
        for name in page_mentioned_brand_names(analysis):
            key = name.lower()
            if key in own_keys or key in seen:
                continue
            seen.add(key)
            items.append({"label": name, "domain": competitor_domains.get(name)})
    return items


def _empty_backlink_detail(domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
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
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    if ctx is None:
        return _empty_backlink_detail(domain)

    prompt_count = ctx.prompt_count

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
        "domain": domain,
        "priority": backlink_priority(prompt_count, ctx.chat_count),
        "platforms": ctx.platforms,
        "citation_count": ctx.citation_count,
        "citation_rate": round(ctx.chat_count / response_total, 4) if response_total else 0,
        "chat_count": ctx.chat_count,
        "prompt_count": prompt_count,
        "mentioned_competitors": _backlink_mentioned_competitors(
            db,
            subject=subject,
            domain=domain,
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        ),
    }


def build_backlink_opportunity_urls_page(
    db: Session,
    *,
    subject: Subject,
    domain: str,
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
        _url_matches_registrable,
    )

    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_total = ctx.chat_count
    eligible = _backlink_window_subquery(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    domain_filter = _backlink_domain_filter(domain, eligible)
    count_expr = func.count(CitationUrl.id)
    grouped = (
        select(
            CitationUrl.url.label("url"),
            count_expr.label("count"),
        )
        .select_from(CitationUrl)
        .join(CitationDomain, CitationDomain.response_id == CitationUrl.response_id)
        .where(
            domain_filter,
            _url_matches_registrable(CitationUrl.url, domain),
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
        .select_from(CitationUrl)
        .join(CitationDomain, CitationDomain.response_id == CitationUrl.response_id)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(
            domain_filter,
            CitationUrl.url.in_(page_urls),
            _url_matches_registrable(CitationUrl.url, domain),
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
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import _normalize_pagination

    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_total = ctx.chat_count
    eligible = _backlink_window_subquery(
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    domain_filter = _backlink_domain_filter(domain, eligible)
    count_expr = func.sum(CitationDomain.cite_count)
    grouped = (
        select(
            CitationDomain.prompt_id.label("prompt_id"),
            count_expr.label("count"),
        )
        .where(domain_filter)
        .group_by(CitationDomain.prompt_id)
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
    topics = (
        db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
        if topic_ids
        else []
    )
    topic_names = {str(topic.id): topic.name for topic in topics}
    count_by_prompt = {prompt_id: int(count) for prompt_id, count in page_rows}

    platform_rows = db.execute(
        select(CitationDomain.prompt_id, LLMResponse.platform)
        .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
        .where(
            domain_filter,
            CitationDomain.prompt_id.in_(page_prompt_ids),
            LLMResponse.platform != "",
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
