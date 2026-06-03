"""Read-time aggregates for MVP dashboards."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    Prompt,
    SamplingJob,
    Subject,
    SubjectType,
    Topic,
)
from aperix_geo.utils.coerce import safe_float, safe_int


def _mentions_own(parsed: dict[str, Any]) -> bool:
    if parsed.get("mentions_own"):
        return True
    return safe_int(parsed, "mention_count_own") > 0


def _responses_in_window(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> list[LLMResponse]:
    stmt = (
        select(LLMResponse)
        .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
        .where(
            and_(
                SamplingJob.subject_id == subject_id,
                LLMResponse.created_at >= dt_from,
                LLMResponse.created_at <= dt_to,
                LLMResponse.status == LLMResponseStatus.success,
            )
        )
    )
    if platforms:
        stmt = stmt.where(LLMResponse.platform.in_(platforms))
    if topic_id is not None:
        stmt = stmt.join(Prompt, LLMResponse.prompt_id == Prompt.id).where(Prompt.topic_id == topic_id)
    return [r for r in db.execute(stmt).scalars().all() if r.parsed]


@dataclass
class MetricsBundle:
    response_count: int
    visibility_rate: float | None
    mention_intensity: float | None
    share_of_voice: float | None
    average_rank: float | None
    citation_rate: float | None
    sentiment_score: float | None
    sentiment_own_counts: dict[str, int]
    citation_coverage: float | None


def compute_subject_metrics(rows: list[LLMResponse], *, subject: Subject) -> MetricsBundle:
    """Compute the six core KPIs from parsed response rows."""
    n = len(rows)
    if n == 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_intensity=None,
            share_of_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_own_counts={"positive": 0, "neutral": 0, "negative": 0},
            citation_coverage=None,
        )

    mention_rows = 0
    mention_count_total = 0
    competitor_voice_total = 0
    ranks: list[float] = []
    cited_when_mentioned = 0
    sentiment_scores: list[float] = []
    sentiment_own_counts: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    cited_all = 0

    for r in rows:
        p = r.parsed or {}
        if _mentions_own(p):
            mention_rows += 1
            if p.get("cited_own_domain"):
                cited_when_mentioned += 1
            score = safe_float(p, "sentiment_score_own")
            if score is not None:
                sentiment_scores.append(score)
            label = p.get("sentiment_own") or "neutral"
            if label not in sentiment_own_counts:
                label = "neutral"
            sentiment_own_counts[label] += 1

        mc_own = safe_int(p, "mention_count_own")
        if mc_own == 0 and _mentions_own(p):
            mc_own = 1
        mention_count_total += mc_own

        comp_counts = p.get("mention_counts_competitors") or {}
        if isinstance(comp_counts, dict):
            competitor_voice_total += sum(int(v) for v in comp_counts.values() if v)

        rank = p.get("rank_own")
        if rank is not None:
            try:
                ranks.append(float(rank))
            except (TypeError, ValueError):
                pass

        if p.get("cited_own_domain"):
            cited_all += 1

    total_voice = mention_count_total + competitor_voice_total
    return MetricsBundle(
        response_count=n,
        visibility_rate=round(mention_rows / n, 4),
        mention_intensity=round(mention_count_total / n, 4),
        share_of_voice=round(mention_count_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        citation_rate=round(cited_when_mentioned / mention_rows, 4) if mention_rows > 0 else None,
        sentiment_score=round(sum(sentiment_scores) / len(sentiment_scores), 4)
        if sentiment_scores
        else None,
        sentiment_own_counts=sentiment_own_counts,
        citation_coverage=round(cited_all / n, 4)
        if subject.type == SubjectType.domain or subject.website_url
        else None,
    )


def build_overview(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    metrics = compute_subject_metrics(rows, subject=subject)
    return {
        "window": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
        "filters": {
            "platforms": platforms or [],
            "topic_id": str(topic_id) if topic_id else None,
        },
        "response_count": metrics.response_count,
        "visibility_rate": metrics.visibility_rate,
        "mention_intensity": metrics.mention_intensity,
        "share_of_voice": metrics.share_of_voice,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "sentiment_score": metrics.sentiment_score,
        "sentiment_own_counts": metrics.sentiment_own_counts,
        "citation_coverage": metrics.citation_coverage,
    }


def _own_label(subject: Subject) -> str:
    if subject.type == SubjectType.brand:
        return subject.brand or subject.domain or "own"
    return subject.domain or "own"


def _rank_labels(subject: Subject) -> list[str]:
    own = _own_label(subject)
    labels: list[str] = [own]
    for b in subject.competitor_brands:
        if b.name not in labels:
            labels.append(b.name)
    for d in subject.competitor_domains:
        if d.domain not in labels:
            labels.append(d.domain)
    return labels


def _accumulate_rank_counts(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    labels: list[str],
) -> tuple[dict[str, int], dict[str, int], int]:
    own = _own_label(subject)
    visibility_counts: dict[str, int] = {lab: 0 for lab in labels}
    voice_counts: dict[str, int] = {lab: 0 for lab in labels}
    total = len(rows)

    for r in rows:
        p = r.parsed or {}
        if _mentions_own(p):
            visibility_counts[own] = visibility_counts.get(own, 0) + 1
            voice_counts[own] = voice_counts.get(own, 0) + max(safe_int(p, "mention_count_own"), 1)

        mc = p.get("mentions_competitors") or {}
        voice_mc = p.get("mention_counts_competitors") or {}
        for lab in labels:
            if lab == own:
                continue
            mentioned = bool(mc.get(lab)) if isinstance(mc, dict) else False
            if mentioned:
                visibility_counts[lab] = visibility_counts.get(lab, 0) + 1
            if isinstance(voice_mc, dict):
                cnt = int(voice_mc.get(lab, 0) or 0)
                if cnt > 0:
                    voice_counts[lab] = voice_counts.get(lab, 0) + cnt
                elif mentioned:
                    voice_counts[lab] = voice_counts.get(lab, 0) + 1

    return visibility_counts, voice_counts, total


def build_rank(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    own = _own_label(subject)
    labels = _rank_labels(subject)
    visibility_counts, voice_counts, total = _accumulate_rank_counts(rows, subject=subject, labels=labels)

    total_voice = sum(voice_counts.values())
    visibility_share = {k: (round(v / total, 4) if total else 0) for k, v in visibility_counts.items()}
    share_of_voice = {
        k: (round(v / total_voice, 4) if total_voice else 0) for k, v in voice_counts.items()
    }

    return {
        "own_label": own,
        "response_count": total,
        "mention_counts": voice_counts,
        "visibility_counts": visibility_counts,
        "visibility_share": visibility_share,
        "share_of_voice": share_of_voice,
    }


def build_topics_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows = _responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
    )
    topic_ids: dict[UUID, list[LLMResponse]] = defaultdict(list)
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    for r in rows:
        p = prompts.get(r.prompt_id)
        if not p:
            continue
        topic_ids[p.topic_id].append(r)

    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for tid, trows in topic_ids.items():
        t = topics.get(tid)
        name = t.name if t else str(tid)
        metrics = compute_subject_metrics(trows, subject=subject) if subject else None
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": name,
                "response_count": len(trows),
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
            }
        )
    return sorted(out, key=lambda x: x["topic_name"])


def build_prompts_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows = _responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
    )
    by_prompt: dict[UUID, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_prompt[r.prompt_id].append(r)
    prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    pmap = {p.id: p for p in prompts}
    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for pid, prows in by_prompt.items():
        p = pmap.get(pid)
        text = p.text if p else ""
        metrics = compute_subject_metrics(prows, subject=subject) if subject else None
        last_parsed = (prows[-1].parsed or {}) if prows else {}
        out.append(
            {
                "prompt_id": str(pid),
                "prompt_text": text[:200],
                "response_count": len(prows),
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "last_sentiment": last_parsed.get("sentiment_own") or last_parsed.get("sentiment_crude"),
            }
        )
    return sorted(out, key=lambda x: x["prompt_text"])


def build_citations(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    host_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for h in (r.parsed or {}).get("url_hosts") or []:
            host_counts[h] += 1
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


def build_daily_visibility_series(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    labels = _rank_labels(subject)
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        day = r.created_at.date()
        by_date[day].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        visibility_counts, _, total = _accumulate_rank_counts(day_rows, subject=subject, labels=labels)
        values = {k: (round(v / total, 4) if total else 0) for k, v in visibility_counts.items()}
        series.append({"date": day.isoformat(), "values": values, "response_count": total})

    return {
        "own_label": _own_label(subject),
        "labels": labels,
        "series": series,
    }


def build_platform_performance(
    db: Session,
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> list[dict[str, Any]]:
    rows = _responses_in_window(
        db,
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    by_platform: dict[str, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_platform[r.platform].append(r)

    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for platform, mrows in by_platform.items():
        metrics = compute_subject_metrics(mrows, subject=subject) if subject else None
        out.append(
            {
                "platform": platform,
                "response_count": len(mrows),
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


def build_citation_brand_rank(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    own = _own_label(subject)
    labels = _rank_labels(subject)
    total = len(rows)
    cite_counts: dict[str, int] = {lab: 0 for lab in labels}

    for r in rows:
        p = r.parsed or {}
        hosts = p.get("url_hosts") or []
        host_str = " ".join(str(h) for h in hosts) if isinstance(hosts, list) else ""
        for lab in labels:
            if lab == own:
                if p.get("cited_own_domain"):
                    cite_counts[own] += 1
            elif lab in host_str:
                cite_counts[lab] += 1

    citation_share = {k: (round(v / total, 4) if total else 0) for k, v in cite_counts.items()}
    return {
        "own_label": own,
        "response_count": total,
        "citation_counts": cite_counts,
        "citation_share": citation_share,
    }


def build_daily_sentiment_series(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        scores: list[float] = []
        for r in day_rows:
            score = safe_float(r.parsed or {}, "sentiment_score_own")
            if score is not None:
                scores.append(score)
        series.append(
            {
                "date": day.isoformat(),
                "value": round(sum(scores) / len(scores), 4) if scores else None,
                "response_count": len(day_rows),
            }
        )

    return {"own_label": _own_label(subject), "series": series}
