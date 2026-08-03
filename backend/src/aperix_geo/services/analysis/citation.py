"""Citation share and citation analysis builders."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.analysis._series import (
    align_previous_daily_to_current,
    previous_date_range,
    slim_daily_series,
)
from aperix_geo.services.analysis.citation_sql import query_citation
from aperix_geo.services.analysis._page import build_rank_table_rows, previous_value
from aperix_geo.services.analysis.entity import (
    entity_chart_labels,
    list_analysis_entities,
    own_entity,
    resolve_analysis_entity,
)
from aperix_geo.utils.net import citation_registrable_key
from aperix_geo.services.domain.taxonomy import normalize_domain_type
from aperix_geo.services.sampling.citation.aggregate import (
    domain_cite_stats,
    domain_daily_citation_series,
    domain_platform_breakdown,
    domain_topic_breakdown,
    paginate_citation_domain_prompts,
    paginate_citation_domains,
    paginate_citation_urls,
)


def _domain_profile_fields(db: Session, domain: str) -> tuple[str, str]:
    from sqlalchemy import select

    from aperix_geo.db.models import DomainProfile

    row = db.execute(
        select(DomainProfile.site_name, DomainProfile.domain_type).where(
            DomainProfile.domain == domain,
            DomainProfile.deleted.is_(False),
        )
    ).one_or_none()
    if row is None:
        return "", normalize_domain_type("")
    return str(row.site_name or "").strip(), normalize_domain_type(str(row.domain_type or ""))


def build_citation_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """引用率页概览：品牌趋势 + 排名（扁平化；域名/URL 明细见独立分页接口）。"""
    focus_entity = resolve_analysis_entity(subject, entity_id)
    entities = list_analysis_entities(subject)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    own = own_entity(subject)

    overview = query_citation(
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
    citation_share = overview["current_share"]
    prev_share = overview["prev_share"]
    has_previous = overview["has_previous"]
    focus_label = focus_entity.label
    labels = entity_chart_labels(entities)

    series = slim_daily_series(overview["daily_series"], labels)
    prev_raw = overview["prev_daily_series"]

    return {
        "entity_id": focus_entity.id,
        "own_label": own.label,
        "focus_label": focus_label,
        "labels": labels,
        "citation_rate": citation_share.get(focus_label),
        "citation_previous": previous_value(
            prev_share.get(focus_label),
            has_previous=has_previous,
        ),
        "series": series,
        "previous_series": align_previous_daily_to_current(
            series,
            prev_raw,
            labels,
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "rank_table": build_rank_table_rows(
            citation_share,
            prev_share,
            entities=entities,
            has_previous=has_previous,
        ),
    }


def build_citation_domains_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    return paginate_citation_domains(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by="count",  # type: ignore[arg-type]
        order=order,
    )


def build_citation_urls_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    safe_sort = sort_by if sort_by in ("count", "citation_rate") else "count"
    return paginate_citation_urls(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        search=search,
        subject=subject,
        page=page,
        page_size=page_size,
        sort_by=safe_sort,  # type: ignore[arg-type]
        order=order,
    )


def _align_flat_daily_count(
    current_series: list[dict[str, Any]],
    previous_series: list[dict[str, Any]],
    *,
    current_start: date,
    previous_start: date,
) -> list[dict[str, Any]]:
    wrapped_current = [
        {"date": point["date"], "values": {"count": point.get("count", 0)}}
        for point in current_series
    ]
    wrapped_previous = [
        {"date": point["date"], "values": {"count": point.get("count", 0)}}
        for point in previous_series
    ]
    aligned = align_previous_daily_to_current(
        wrapped_current,
        wrapped_previous,
        ["count"],
        current_start=current_start,
        previous_start=previous_start,
    )
    return [
        {"date": point["date"], "count": point["values"].get("count", 0)}
        for point in aligned
    ]


def build_citation_domain_analysis(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """Single-domain overview: totals, daily trend, topic/platform breakdown (SQL-only)."""
    domain = citation_registrable_key(domain)
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    window = {
        "subject_id": subject.id,
        "platform": platform,
        "topic_id": topic_id,
        "prompt_id": prompt_id,
    }

    count, response_total = domain_cite_stats(
        db, dt_from=dt_from, dt_to=dt_to, domain=domain, **window
    )
    prev_count, _ = domain_cite_stats(
        db, dt_from=prev_from, dt_to=prev_to, domain=domain, **window
    )

    series = domain_daily_citation_series(
        db, dt_from=dt_from, dt_to=dt_to, domain=domain, **window
    )
    prev_raw = domain_daily_citation_series(
        db, dt_from=prev_from, dt_to=prev_to, domain=domain, **window
    )

    site_name, domain_type = _domain_profile_fields(db, domain)

    return {
        "domain": domain,
        "count": count,
        "citation_rate": round(count / response_total, 4) if response_total else 0,
        "prev_count": prev_count,
        "response_total": response_total,
        "series": series,
        "previous_series": _align_flat_daily_count(
            series,
            prev_raw,
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "topics": domain_topic_breakdown(
            db,
            dt_from=dt_from,
            dt_to=dt_to,
            domain=domain,
            response_total=response_total,
            **window,
        ),
        "platforms": domain_platform_breakdown(
            db,
            dt_from=dt_from,
            dt_to=dt_to,
            domain=domain,
            response_total=response_total,
            **window,
        ),
        "site_name": site_name,
        "domain_type": domain_type,
    }


def build_citation_domain_urls_page(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    safe_sort = sort_by if sort_by in ("count", "citation_rate") else "count"
    domain = citation_registrable_key(domain)
    return paginate_citation_urls(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        domain=domain,
        subject=subject,
        page=page,
        page_size=page_size,
        sort_by=safe_sort,  # type: ignore[arg-type]
        order=order,
    )


def build_citation_domain_prompts_page(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    safe_sort = sort_by if sort_by in ("count", "citation_rate") else "count"
    domain = citation_registrable_key(domain)
    return paginate_citation_domain_prompts(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        domain=domain,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        page=page,
        page_size=page_size,
        sort_by=safe_sort,  # type: ignore[arg-type]
        order=order,
    )
