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
from aperix_geo.services.analysis.aggregate import (
    citation_share_from_signals,
    daily_citation_share_series_from_signals,
)
from aperix_geo.services.analysis.dashboard import _build_rank_table_rows, _previous_value
from aperix_geo.services.analysis.entity import (
    entity_chart_labels,
    list_analysis_entities,
    resolve_analysis_entity,
)
from aperix_geo.services.analysis.signal_index import build_dual_signal_window, window_has_data
from aperix_geo.services.analysis.signal_load import load_llm_response_signals
from aperix_geo.services.sampling.citation.aggregate import (
    domain_cite_stats,
    domain_daily_citation_series,
    domain_platform_breakdown,
    domain_topic_breakdown,
    paginate_citation_domain_prompts,
    paginate_citation_domains,
    paginate_citation_urls,
)


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

    all_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=prev_from,
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
    has_previous = window_has_data(windows.previous)

    current_signals = [row for rows in windows.current.by_date.values() for row in rows]
    prev_signals = [row for rows in windows.previous.by_date.values() for row in rows]

    _cite_counts, citation_share, own = citation_share_from_signals(
        current_signals, subject=subject
    )
    _prev_counts, prev_share, _ = citation_share_from_signals(prev_signals, subject=subject)
    focus_label = focus_entity.label
    labels = entity_chart_labels(entities)

    series = slim_daily_series(
        daily_citation_share_series_from_signals(current_signals, subject=subject),
        labels,
    )
    prev_raw = daily_citation_share_series_from_signals(prev_signals, subject=subject)

    return {
        "entity_id": focus_entity.id,
        "own_label": own,
        "focus_label": focus_label,
        "labels": labels,
        "citation_rate": citation_share.get(focus_label),
        "citation_previous": _previous_value(
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
        "rank_table": _build_rank_table_rows(
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
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """Single-domain overview: totals, daily trend, topic/platform breakdown (SQL-only)."""
    host = (host or "").strip().lower()
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    window = {
        "subject_id": subject.id,
        "platform": platform,
        "topic_id": topic_id,
        "prompt_id": prompt_id,
    }

    count, response_total = domain_cite_stats(
        db, dt_from=dt_from, dt_to=dt_to, host=host, **window
    )
    prev_count, _ = domain_cite_stats(
        db, dt_from=prev_from, dt_to=prev_to, host=host, **window
    )

    series = domain_daily_citation_series(
        db, dt_from=dt_from, dt_to=dt_to, host=host, **window
    )
    prev_raw = domain_daily_citation_series(
        db, dt_from=prev_from, dt_to=prev_to, host=host, **window
    )

    return {
        "host": host,
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
            host=host,
            response_total=response_total,
            **window,
        ),
        "platforms": domain_platform_breakdown(
            db,
            dt_from=dt_from,
            dt_to=dt_to,
            host=host,
            response_total=response_total,
            **window,
        ),
    }


def build_citation_domain_urls_page(
    db: Session,
    *,
    subject: Subject,
    host: str,
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
    return paginate_citation_urls(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        host=host,
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
    host: str,
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
    return paginate_citation_domain_prompts(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        host=host,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
        page=page,
        page_size=page_size,
        sort_by=safe_sort,  # type: ignore[arg-type]
        order=order,
    )
