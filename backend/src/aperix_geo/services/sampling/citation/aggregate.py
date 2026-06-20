"""Aggregate citation counts across LLM responses in a time window.

Reads ``tb_citation_domains`` and ``tb_citation_urls`` as the authoritative source.
JSONB ``LLMResponse.parsed`` is not used for aggregation.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, LLMResponse, Prompt, Subject, Topic
from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names
from aperix_geo.services.subject.labels import competitor_rank_label
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.text import coalesce_page_title, is_template_title, mode_nonempty
from aperix_geo.utils.url import hostname_from_url

CitationDomainSortField = Literal["count"]
CitationUrlSortField = Literal["count", "citation_rate"]
CitationDomainPromptSortField = Literal["count", "citation_rate"]
_MAX_PAGE_SIZE = 100


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
    page_title = mode_nonempty(
        [
            record.page_title
            for record in records
            if record.page_title and not is_template_title(record.page_title)
        ]
    )
    url_type = mode_nonempty([record.url_type for record in records])
    domain_type = mode_nonempty([record.domain_type for record in records])

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
        "title": coalesce_page_title(page_title, url=url),
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
    """Domain-level citation counts for a response window (from tb_citation_domains)."""
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
    host_counts = {domain: int(count) for domain, count, _ in db_rows if domain}
    domain_types = {domain: str(domain_type or "").strip() for domain, _, domain_type in db_rows if domain}
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
    """URL-level citation counts and source-page metadata (from tb_citation_urls)."""
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

    prompt_ids = {record.prompt_id for record in records}
    prompt_map, topic_names = _load_prompt_topic_maps(db, prompt_ids)

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


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
    return safe_page, safe_page_size


def _ilike_pattern(needle: str) -> str:
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _citation_search_text(search: str | None) -> str | None:
    text = (search or "").strip()
    return text or None


def domain_search_needle(search: str | None) -> str | None:
    """Normalize user input for domain host substring match."""
    text = _citation_search_text(search)
    if not text:
        return None
    if "://" in text or text.startswith("//"):
        raw = text if not text.startswith("//") else f"https:{text}"
        host = hostname_from_url(raw)
    elif "/" in text and "." in text.split("/", 1)[0]:
        host = hostname_from_url(f"https://{text}")
    else:
        host = text.split("/", 1)[0]
    if not host:
        return text.lower()
    root = registrable_domain(host) or host.strip().lower()
    return root.lower()


def url_search_needle(search: str | None) -> str | None:
    text = _citation_search_text(search)
    return text.lower() if text else None


def _window_kwargs(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    prompt_id: UUID | None,
) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "dt_from": dt_from,
        "dt_to": dt_to,
        "platform": platform,
        "topic_id": topic_id,
        "prompt_id": prompt_id,
    }


def paginate_citation_domains(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: CitationDomainSortField = "count",
    order: str = "desc",
) -> dict[str, Any]:
    """Paginated domain citation rows (SQL group-by, no full response load)."""
    from aperix_geo.services.analysis._query import (
        count_responses_in_window,
        response_ids_in_window_stmt,
    )

    _ = sort_by  # only count supported; reserved for future columns
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    window = _window_kwargs(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    response_total = count_responses_in_window(db, **window)
    if response_total == 0:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    id_subq = response_ids_in_window_stmt(**window).subquery()
    count_expr = func.sum(CitationDomain.cite_count)
    domain_filters = [CitationDomain.response_id.in_(select(id_subq.c.id))]
    domain_needle = domain_search_needle(search)
    if domain_needle:
        domain_filters.append(CitationDomain.domain.ilike(_ilike_pattern(domain_needle)))
    grouped = (
        select(
            CitationDomain.domain.label("host"),
            count_expr.label("count"),
            func.max(CitationDomain.domain_type).label("domain_type"),
        )
        .where(*domain_filters)
        .group_by(CitationDomain.domain)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    order_clause = (
        grouped.c.count.asc() if order == "asc" else grouped.c.count.desc()
    )
    offset = (safe_page - 1) * safe_page_size
    rows = db.execute(
        select(grouped.c.host, grouped.c.count, grouped.c.domain_type)
        .order_by(order_clause, grouped.c.host.asc())
        .offset(offset)
        .limit(safe_page_size)
    ).all()

    items = [
        {
            "host": str(host or "").strip().lower(),
            "count": int(count or 0),
            "citation_rate": round(int(count or 0) / response_total, 4),
            "domain_type": str(domain_type or "").strip() or None,
        }
        for host, count, domain_type in rows
        if host
    ]
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }


def _normalize_host(host: str) -> str:
    return (host or "").strip().lower()


def _url_matches_host(url_column, host: str):
    """SQL filter: citation URL belongs to registrable host (matches persist hostname logic)."""
    host = _normalize_host(host)
    if not host:
        return or_(False)
    roots = {host}
    if host.startswith("www."):
        roots.add(host[4:])
    else:
        roots.add(f"www.{host}")
    clauses = []
    for label in roots:
        clauses.append(url_column.ilike(f"%://{label}/%"))
        clauses.append(url_column.ilike(f"%://{label}"))
    return or_(*clauses)


def domain_cite_stats(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    host: str,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> tuple[int, str | None, int]:
    """Return (cite_count, domain_type, response_total) for one host in window."""
    from aperix_geo.services.analysis._query import (
        count_responses_in_window,
        response_ids_in_window_stmt,
    )

    host = _normalize_host(host)
    window = _window_kwargs(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    response_total = count_responses_in_window(db, **window)
    if response_total == 0 or not host:
        return 0, None, response_total

    id_subq = response_ids_in_window_stmt(**window).subquery()
    count, domain_type = db.execute(
        select(
            func.coalesce(func.sum(CitationDomain.cite_count), 0),
            func.max(CitationDomain.domain_type),
        ).where(
            CitationDomain.response_id.in_(select(id_subq.c.id)),
            CitationDomain.domain == host,
        )
    ).one()
    dtype = str(domain_type or "").strip() or None
    return int(count or 0), dtype, response_total


def domain_daily_citation_series(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    host: str,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis._query import response_ids_in_window_stmt

    host = _normalize_host(host)
    if not host:
        return []

    id_subq = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    ).subquery()
    day_expr = func.date(LLMResponse.created_at)
    rows = db.execute(
        select(day_expr.label("day"), func.sum(CitationDomain.cite_count).label("count"))
        .select_from(CitationDomain)
        .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
        .where(
            CitationDomain.response_id.in_(select(id_subq.c.id)),
            CitationDomain.domain == host,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    ).all()
    return [
        {"date": day.isoformat(), "count": int(count or 0)}
        for day, count in rows
        if day is not None
    ]


def _breakdown_rows(
    counts: dict[str, int],
    names: dict[str, str],
    *,
    response_total: int,
    fallback_name: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "id": key,
                "name": names.get(key) or fallback_name,
                "count": count,
                "citation_rate": round(count / response_total, 4) if response_total else 0,
            }
            for key, count in counts.items()
        ],
        key=lambda row: -row["count"],
    )


def domain_topic_breakdown(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    host: str,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    response_total: int,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis._query import response_ids_in_window_stmt

    host = _normalize_host(host)
    if not host or response_total == 0:
        return []

    id_subq = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    ).subquery()
    rows = db.execute(
        select(Prompt.topic_id, func.count(CitationDomain.response_id))
        .select_from(CitationDomain)
        .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
        .join(Prompt, LLMResponse.prompt_id == Prompt.id)
        .where(
            CitationDomain.response_id.in_(select(id_subq.c.id)),
            CitationDomain.domain == host,
        )
        .group_by(Prompt.topic_id)
    ).all()
    counts = {str(topic_id): int(count) for topic_id, count in rows if topic_id is not None}
    if not counts:
        return []
    topic_rows = db.execute(
        select(Topic).where(Topic.id.in_([UUID(tid) for tid in counts]))
    ).scalars().all()
    names = {str(topic.id): topic.name for topic in topic_rows}
    return _breakdown_rows(counts, names, response_total=response_total, fallback_name="未知主题")


def domain_platform_breakdown(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    host: str,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    response_total: int,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis._query import response_ids_in_window_stmt

    host = _normalize_host(host)
    if not host or response_total == 0:
        return []

    id_subq = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    ).subquery()
    rows = db.execute(
        select(LLMResponse.platform, func.count(CitationDomain.response_id))
        .select_from(CitationDomain)
        .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
        .where(
            CitationDomain.response_id.in_(select(id_subq.c.id)),
            CitationDomain.domain == host,
        )
        .group_by(LLMResponse.platform)
    ).all()
    counts = {
        str(platform or "").strip(): int(count)
        for platform, count in rows
        if str(platform or "").strip()
    }
    names = dict.fromkeys(counts, "")
    for platform in counts:
        names[platform] = platform
    return _breakdown_rows(counts, names, response_total=response_total, fallback_name="未知平台")


def paginate_citation_domain_prompts(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    host: str,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: CitationDomainPromptSortField = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.analysis._query import (
        count_responses_in_window,
        response_ids_in_window_stmt,
    )

    host = _normalize_host(host)
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    window = _window_kwargs(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    response_total = count_responses_in_window(db, **window)
    if response_total == 0 or not host:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": response_total,
        }

    id_subq = response_ids_in_window_stmt(**window).subquery()
    count_expr = func.count(CitationDomain.response_id)
    grouped = (
        select(
            CitationDomain.prompt_id.label("prompt_id"),
            count_expr.label("count"),
        )
        .where(
            CitationDomain.response_id.in_(select(id_subq.c.id)),
            CitationDomain.domain == host,
        )
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
    _ = sort_by  # citation_rate sort ≡ count sort (same denominator)

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
    items = [
        {
            "id": str(prompt_id),
            "name": (prompt_map.get(prompt_id) and prompt_map[prompt_id].text) or "未知提示词",
            "topic_name": topic_names.get(
                str(prompt_map[prompt_id].topic_id) if prompt_id in prompt_map else "",
                "未知主题",
            ),
            "count": count_by_prompt.get(prompt_id, 0),
            "citation_rate": round(count_by_prompt.get(prompt_id, 0) / response_total, 4),
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


def paginate_citation_urls(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    host: str | None = None,
    search: str | None = None,
    subject: Subject | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: CitationUrlSortField = "count",
    order: str = "desc",
) -> dict[str, Any]:
    """Paginated URL citation rows: SQL page of URLs, then hydrate metadata for page only."""
    from aperix_geo.services.analysis._query import (
        count_responses_in_window,
        response_ids_in_window_stmt,
    )

    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    window = _window_kwargs(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    response_total = count_responses_in_window(db, **window)
    if response_total == 0:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    id_subq = response_ids_in_window_stmt(**window).subquery()
    count_expr = func.count(CitationUrl.id)
    url_filters = [CitationUrl.response_id.in_(select(id_subq.c.id))]
    host_needle = _normalize_host(host) if host else ""
    if host_needle:
        url_filters.append(_url_matches_host(CitationUrl.url, host_needle))
    url_needle = url_search_needle(search)
    if url_needle:
        url_filters.append(CitationUrl.url.ilike(_ilike_pattern(url_needle)))
    grouped = (
        select(
            CitationUrl.url.label("url"),
            count_expr.label("count"),
        )
        .where(*url_filters)
        .group_by(CitationUrl.url)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    # citation_rate = count / response_total; sort_by citation_rate ≡ sort by count
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

    records = db.execute(
        select(CitationUrl).where(
            CitationUrl.url.in_(page_urls),
            CitationUrl.response_id.in_(select(id_subq.c.id)),
        )
    ).scalars().all()

    grouped_records: dict[str, list[CitationUrl]] = defaultdict(list)
    for record in records:
        grouped_records[record.url].append(record)

    prompt_ids = {record.prompt_id for record in records}
    prompt_map, topic_names = _load_prompt_topic_maps(db, prompt_ids)
    competitor_domains = _competitor_domain_map(subject)

    items = [
        _aggregate_url_row(
            url,
            grouped_records.get(url, []),
            total=response_total,
            competitor_domains=competitor_domains,
            prompt_map=prompt_map,
            topic_names=topic_names,
        )
        for url in page_urls
    ]

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }
