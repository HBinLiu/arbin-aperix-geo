"""Citation share and citation analysis builders."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, LLMResponse, Prompt, Subject, Topic
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
from aperix_geo.services.sampling.citation import (
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


def _domain_cite_count(db: Session, rows: list[LLMResponse], host: str) -> int:
    if not rows or not host:
        return 0
    response_ids = [r.id for r in rows]
    total = db.execute(
        select(func.coalesce(func.sum(CitationDomain.cite_count), 0)).where(
            CitationDomain.response_id.in_(response_ids),
            CitationDomain.domain == host,
        )
    ).scalar_one()
    if total:
        return int(total)
    tally = 0
    for r in rows:
        for h in (r.parsed or {}).get("url_hosts") or []:
            if str(h).strip().lower() == host:
                tally += 1
                break
    return tally


def _responses_citing_host(db: Session, rows: list[LLMResponse], host: str) -> list[LLMResponse]:
    if not rows or not host:
        return []
    host = host.strip().lower()
    response_ids = [r.id for r in rows]
    citing_ids = set(
        db.execute(
            select(CitationDomain.response_id).where(
                CitationDomain.response_id.in_(response_ids),
                CitationDomain.domain == host,
            )
        )
        .scalars()
        .all()
    )
    if citing_ids:
        return [r for r in rows if r.id in citing_ids]
    return [
        r
        for r in rows
        if host
        in {str(h).strip().lower() for h in (r.parsed or {}).get("url_hosts") or [] if h}
    ]


def _domain_breakdown_rows(
    counts: dict[str, int],
    names: dict[str, str],
    *,
    total: int,
    fallback_name: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "id": key,
                "name": names.get(key) or fallback_name,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
            }
            for key, count in counts.items()
        ],
        key=lambda row: -row["count"],
    )


def _aggregate_domain_prompts(
    db: Session,
    citing_rows: list[LLMResponse],
    *,
    total: int,
) -> list[dict[str, Any]]:
    if not citing_rows:
        return []
    counts: dict[str, int] = defaultdict(int)
    for row in citing_rows:
        counts[str(row.prompt_id)] += 1
    prompt_ids = [UUID(pid) for pid in counts]
    prompts = db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids))).scalars().all()
    names = {str(prompt.id): prompt.text for prompt in prompts}
    topic_ids = {prompt.topic_id for prompt in prompts}
    topics = (
        db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
        if topic_ids
        else []
    )
    topic_names = {str(topic.id): topic.name for topic in topics}
    prompt_topic_names = {
        str(prompt.id): topic_names.get(str(prompt.topic_id), "未知主题") for prompt in prompts
    }
    return sorted(
        [
            {
                "id": key,
                "name": names.get(key) or "未知提示词",
                "topic_name": prompt_topic_names.get(key, "未知主题"),
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
            }
            for key, count in counts.items()
        ],
        key=lambda row: -row["count"],
    )


def _aggregate_domain_topics(
    db: Session,
    citing_rows: list[LLMResponse],
    *,
    total: int,
) -> list[dict[str, Any]]:
    if not citing_rows:
        return []
    prompt_ids = {row.prompt_id for row in citing_rows}
    prompt_rows = db.execute(
        select(Prompt.id, Prompt.topic_id).where(Prompt.id.in_(prompt_ids))
    ).all()
    prompt_to_topic = {prompt_id: topic_id for prompt_id, topic_id in prompt_rows}
    counts: dict[str, int] = defaultdict(int)
    for row in citing_rows:
        topic_id = prompt_to_topic.get(row.prompt_id)
        if topic_id is not None:
            counts[str(topic_id)] += 1
    topic_ids = [UUID(tid) for tid in counts]
    topics = db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
    names = {str(topic.id): topic.name for topic in topics}
    return _domain_breakdown_rows(counts, names, total=total, fallback_name="未知主题")


def _aggregate_domain_platforms(
    citing_rows: list[LLMResponse],
    *,
    total: int,
) -> list[dict[str, Any]]:
    if not citing_rows:
        return []
    counts: dict[str, int] = defaultdict(int)
    for row in citing_rows:
        platform = (row.platform or "").strip()
        if platform:
            counts[platform] += 1
    names = dict.fromkeys(counts, "")
    for platform in counts:
        names[platform] = platform
    return _domain_breakdown_rows(counts, names, total=total, fallback_name="未知平台")


def _daily_domain_citation_series(
    db: Session,
    rows: list[LLMResponse],
    host: str,
) -> list[dict[str, Any]]:
    if not rows or not host:
        return []
    by_date: dict[date, int] = defaultdict(int)
    response_ids = [r.id for r in rows]
    id_to_date = {r.id: r.created_at.date() for r in rows}

    db_rows = db.execute(
        select(CitationDomain.response_id, CitationDomain.cite_count).where(
            CitationDomain.response_id.in_(response_ids),
            CitationDomain.domain == host,
        )
    ).all()
    if db_rows:
        for response_id, cite_count in db_rows:
            day = id_to_date.get(response_id)
            if day is not None:
                by_date[day] += int(cite_count or 0)
    else:
        for r in rows:
            hosts = {str(h).strip().lower() for h in (r.parsed or {}).get("url_hosts") or [] if h}
            if host in hosts:
                by_date[r.created_at.date()] += 1

    return [{"date": day.isoformat(), "values": {"count": by_date[day]}} for day in sorted(by_date.keys())]


def build_citation_domain_analysis(
    db: Session,
    *,
    subject: Subject,
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """Single-domain citation drill-down: totals, daily counts, URL list."""
    host = (host or "").strip().lower()
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

    domain_rows = aggregate_citation_domains(db, current_rows)
    match = next((row for row in domain_rows if row.get("host") == host), None)
    count = int(match["count"]) if match else _domain_cite_count(db, current_rows, host)
    prev_count = _domain_cite_count(db, prev_rows, host)
    total = len(current_rows)

    series = _daily_domain_citation_series(db, current_rows, host)
    prev_raw = _daily_domain_citation_series(db, prev_rows, host)
    citing_rows = _responses_citing_host(db, current_rows, host)

    return {
        "host": host,
        "count": count,
        "citation_rate": round(count / total, 4) if total else 0,
        "domain_type": (match or {}).get("domain_type"),
        "prev_count": prev_count,
        "series": series,
        "previous_series": align_previous_daily_to_current(
            series,
            prev_raw,
            ["count"],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "urls": [
            row
            for row in aggregate_citation_urls(db, current_rows, subject=subject)
            if row.get("host") == host
        ],
        "prompts": _aggregate_domain_prompts(db, citing_rows, total=total),
        "topics": _aggregate_domain_topics(db, citing_rows, total=total),
        "platforms": _aggregate_domain_platforms(citing_rows, total=total),
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
