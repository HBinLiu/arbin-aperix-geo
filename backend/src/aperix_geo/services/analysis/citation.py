"""Citation share and citation analysis builders."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, Subject
from aperix_geo.services.analysis._labels import own_label, rank_labels
from aperix_geo.services.analysis._parsed import cited_competitor_on_source
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import (
    align_previous_daily_to_current,
    previous_date_range,
    slim_daily_series,
    top_visibility_labels,
)
from aperix_geo.services.analysis.overview import build_overview
from aperix_geo.services.sampling.citations import (
    aggregate_citation_domains as aggregate_citation_domains_from_db,
    aggregate_citation_urls as aggregate_citation_urls_from_db,
)


def citation_share_by_label(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    labels: list[str],
) -> dict[str, float | None]:
    own = own_label(subject)
    total = len(rows)
    if total == 0:
        return {lab: None for lab in labels}
    cite_counts: dict[str, int] = {lab: 0 for lab in labels}
    for r in rows:
        p = r.parsed or {}
        for lab in labels:
            if lab == own:
                if p.get("cited_own_domain"):
                    cite_counts[own] += 1
            elif cited_competitor_on_source(p, lab):
                cite_counts[lab] += 1
    return {k: round(v / total, 4) for k, v in cite_counts.items()}


def citation_share_from_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
) -> tuple[dict[str, int], dict[str, float], str]:
    own = own_label(subject)
    labels = rank_labels(subject)
    total = len(rows)
    cite_counts: dict[str, int] = {lab: 0 for lab in labels}

    for r in rows:
        p = r.parsed or {}
        for lab in labels:
            if lab == own:
                if p.get("cited_own_domain"):
                    cite_counts[own] += 1
            elif cited_competitor_on_source(p, lab):
                cite_counts[lab] += 1

    citation_share = {k: (round(v / total, 4) if total else 0) for k, v in cite_counts.items()}
    return cite_counts, citation_share, own


def daily_citation_share_series(
    rows: list[LLMResponse],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    labels = rank_labels(subject)
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        _, citation_share, _ = citation_share_from_rows(by_date[day], subject=subject)
        series.append({"date": day.isoformat(), "values": {lab: citation_share.get(lab, 0) for lab in labels}})
    return series


def aggregate_citation_domains(db: Session, rows: list[LLMResponse]) -> list[dict[str, Any]]:
    return aggregate_citation_domains_from_db(db, rows)


def aggregate_citation_urls(db: Session, rows: list[LLMResponse], *, subject: Subject | None = None) -> list[dict[str, Any]]:
    return aggregate_citation_urls_from_db(db, rows, subject=subject)


def build_citations(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    host_counts: dict[str, int] = defaultdict(int)
    domain_rows = aggregate_citation_domains_from_db(db, rows)
    for row in domain_rows:
        host_counts[row["host"]] = row["count"]
    top_hosts = sorted(host_counts.items(), key=lambda x: -x[1])[:50]
    overview = build_overview(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    return {
        "subject_type": subject.type.value,
        "url_host_counts": [{"host": h, "count": c} for h, c in top_hosts],
        "citation_coverage": overview.get("citation_coverage"),
        "citation_rate": overview.get("citation_rate"),
    }


def build_citation_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """引用率页：品牌趋势、排名、域名/URL 明细。"""
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    all_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    current_rows = [r for r in all_rows if dt_from <= r.created_at <= dt_to]
    prev_rows = [r for r in all_rows if prev_from <= r.created_at <= prev_to]

    cite_counts, citation_share, own = citation_share_from_rows(current_rows, subject=subject)
    prev_counts, prev_share, _ = citation_share_from_rows(prev_rows, subject=subject)
    labels = top_visibility_labels(citation_share, own)

    series = slim_daily_series(daily_citation_share_series(current_rows, subject=subject), labels)
    prev_raw = daily_citation_share_series(prev_rows, subject=subject)

    return {
        "own_label": own,
        "labels": labels,
        "citation_rate": citation_share.get(own),
        "rank": {
            "own_label": own,
            "citation_counts": cite_counts,
            "citation_share": citation_share,
        },
        "previous_rank": {
            "own_label": own,
            "citation_counts": prev_counts,
            "citation_share": prev_share,
        },
        "series": series,
        "previous_series": align_previous_daily_to_current(
            series,
            prev_raw,
            labels,
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "domains": aggregate_citation_domains(db, current_rows),
        "urls": aggregate_citation_urls(db, current_rows, subject=subject),
    }


def build_citation_brand_rank(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    cite_counts, citation_share, own = citation_share_from_rows(rows, subject=subject)
    return {
        "own_label": own,
        "citation_counts": cite_counts,
        "citation_share": citation_share,
    }
