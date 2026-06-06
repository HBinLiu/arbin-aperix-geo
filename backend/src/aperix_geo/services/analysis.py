"""Read-time aggregates for MVP dashboards."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
    prompt_id: UUID | None = None,
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
    if prompt_id is not None:
        stmt = stmt.where(LLMResponse.prompt_id == prompt_id)
    return [r for r in db.execute(stmt).scalars().all() if r.parsed]


@dataclass
class MetricsBundle:
    response_count: int
    visibility_rate: float | None
    mention_intensity: float | None
    share_voice: float | None
    average_rank: float | None
    citation_rate: float | None
    sentiment_score: float | None
    sentiment_count: dict[str, int]
    citation_coverage: float | None


def compute_subject_metrics(rows: list[LLMResponse], *, subject: Subject) -> MetricsBundle:
    """Compute the six core KPIs from parsed response rows."""
    n = len(rows)
    if n == 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_intensity=None,
            share_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_count={"positive": 0, "neutral": 0, "negative": 0},
            citation_coverage=None,
        )

    mention_rows = 0
    mention_count_total = 0
    competitor_voice_total = 0
    ranks: list[float] = []
    cited_when_mentioned = 0
    sentiment_scores: list[float] = []
    sentiment_count: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
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
            if label not in sentiment_count:
                label = "neutral"
            sentiment_count[label] += 1

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
        share_voice=round(mention_count_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        citation_rate=round(cited_when_mentioned / mention_rows, 4) if mention_rows > 0 else None,
        sentiment_score=round(sum(sentiment_scores) / len(sentiment_scores), 4)
        if sentiment_scores
        else None,
        sentiment_count=sentiment_count,
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
        "visibility_rate": metrics.visibility_rate,
        "mention_intensity": metrics.mention_intensity,
        "share_voice": metrics.share_voice,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
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


def _rank_positions_from_parsed(p: dict[str, Any], labels: list[str]) -> dict[str, int | None]:
    """按 rank_hints_first_index 计算各品牌在单条回复中的出现顺位（1 最好）。"""
    hints = p.get("rank_hints_first_index") or {}
    if not isinstance(hints, dict):
        hints = {}
    mentioned: list[tuple[str, int]] = []
    for lab in labels:
        idx = hints.get(lab)
        if idx is not None:
            try:
                mentioned.append((lab, int(idx)))
            except (TypeError, ValueError):
                continue
    mentioned.sort(key=lambda x: x[1])
    out: dict[str, int | None] = {lab: None for lab in labels}
    for rank, (lab, _) in enumerate(mentioned, start=1):
        out[lab] = rank
    return out


def _accumulate_average_ranks(
    rows: list[LLMResponse],
    *,
    labels: list[str],
    own: str,
) -> dict[str, float | None]:
    """各品牌平均排名：仅统计该品牌在该条回复中有名次的样本。"""
    buckets: dict[str, list[float]] = {lab: [] for lab in labels}
    for r in rows:
        p = r.parsed or {}
        positions = _rank_positions_from_parsed(p, labels)
        for lab in labels:
            if lab == own:
                ro = p.get("rank_own")
                if ro is not None:
                    try:
                        buckets[lab].append(float(ro))
                        continue
                    except (TypeError, ValueError):
                        pass
            pos = positions.get(lab)
            if pos is not None:
                buckets[lab].append(float(pos))
    return {lab: (round(sum(v) / len(v), 2) if v else None) for lab, v in buckets.items()}


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


def _rank_from_rows(rows: list[LLMResponse], *, subject: Subject) -> dict[str, Any]:
    own = _own_label(subject)
    labels = _rank_labels(subject)
    visibility_counts, voice_counts, total = _accumulate_rank_counts(rows, subject=subject, labels=labels)

    total_voice = sum(voice_counts.values())
    visibility_share = {k: (round(v / total, 4) if total else 0) for k, v in visibility_counts.items()}
    share_voice_map = {
        k: (round(v / total_voice, 4) if total_voice else 0) for k, v in voice_counts.items()
    }

    mention_share = {
        k: (round(v / total, 4) if total else 0) for k, v in voice_counts.items()
    }
    average_rank = _accumulate_average_ranks(rows, labels=labels, own=own)
    _, citation_share, _ = _citation_share_from_rows(rows, subject=subject)
    sentiment_score = _accumulate_sentiment_by_label(rows, labels=labels, own=own)

    return {
        "own_label": own,
        "mention_counts": voice_counts,
        "visibility_counts": visibility_counts,
        "visibility_share": visibility_share,
        "mention_share": mention_share,
        "share_voice": share_voice_map,
        "average_rank": average_rank,
        "citation_share": citation_share,
        "sentiment_score": sentiment_score,
    }


def _accumulate_sentiment_by_label(
    rows: list[LLMResponse],
    *,
    labels: list[str],
    own: str,
) -> dict[str, float | None]:
    """各品牌情感得分：自有品牌用解析结果，竞品在提及时基于原文片段估算。"""
    from aperix_geo.services.sampling.parser import (
        _crude_sentiment,
        _sentences_with_terms,
        _sentiment_score,
    )

    buckets: dict[str, list[float]] = {lab: [] for lab in labels}
    for r in rows:
        p = r.parsed or {}
        text = r.raw_text or ""
        for lab in labels:
            if lab == own:
                if _mentions_own(p):
                    score = safe_float(p, "sentiment_score_own")
                    if score is not None:
                        buckets[lab].append(score)
                continue
            mc = p.get("mentions_competitors") or {}
            if isinstance(mc, dict) and mc.get(lab):
                snippet = _sentences_with_terms(text, [lab])
                if snippet.strip():
                    buckets[lab].append(_sentiment_score(_crude_sentiment(snippet)))
    return {lab: (round(sum(v) / len(v), 4) if v else None) for lab, v in buckets.items()}


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
    return _rank_from_rows(rows, subject=subject)


def _daily_share_series_from_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    metric: str,
) -> list[dict[str, Any]]:
    labels = _rank_labels(subject)
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        visibility_counts, voice_counts, total = _accumulate_rank_counts(day_rows, subject=subject, labels=labels)
        counts = visibility_counts if metric == "visibility" else voice_counts
        if metric == "share_voice":
            total_voice = sum(voice_counts.values())
            values = {k: (round(v / total_voice, 4) if total_voice else 0) for k, v in voice_counts.items()}
        else:
            values = {k: (round(v / total, 4) if total else 0) for k, v in counts.items()}
        series.append({"date": day.isoformat(), "values": values})
    return series


def _daily_average_rank_series_from_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    """自有品牌日均平均排名（仅含 rank_own 有值的回复）。"""
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        ranks: list[float] = []
        for r in by_date[day]:
            ro = (r.parsed or {}).get("rank_own")
            if ro is not None:
                try:
                    ranks.append(float(ro))
                except (TypeError, ValueError):
                    pass
        series.append(
            {
                "date": day.isoformat(),
                "value": round(sum(ranks) / len(ranks), 2) if ranks else None,
            }
        )
    return series


def _align_previous_single_series(
    current_series: list[dict[str, Any]],
    previous_series: list[dict[str, Any]],
    *,
    current_start: date,
    previous_start: date,
) -> list[dict[str, Any]]:
    prev_by_offset: dict[int, dict[str, Any]] = {}
    for pt in previous_series:
        day = date.fromisoformat(pt["date"])
        prev_by_offset[(day - previous_start).days] = pt

    aligned: list[dict[str, Any]] = []
    for pt in current_series:
        day = date.fromisoformat(pt["date"])
        offset = (day - current_start).days
        prev_pt = prev_by_offset.get(offset)
        aligned.append(
            {
                "date": pt["date"],
                "value": prev_pt.get("value") if prev_pt else None,
            }
        )
    return aligned


def build_topics_performance(
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
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
                "response_count": metrics.response_count if metrics else 0,
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
    by_prompt: dict[UUID, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_prompt[r.prompt_id].append(r)
    prompts = db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all()
    pmap = {p.id: p for p in prompts}
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject_id)).scalars().all()
    }
    subject = db.get(Subject, subject_id)
    out: list[dict[str, Any]] = []
    for pid, prows in by_prompt.items():
        p = pmap.get(pid)
        text = p.text if p else ""
        topic = topics.get(p.topic_id) if p else None
        metrics = compute_subject_metrics(prows, subject=subject) if subject else None
        out.append(
            {
                "prompt_id": str(pid),
                "prompt_text": text[:200],
                "topic_id": str(p.topic_id) if p else None,
                "topic_name": topic.name if topic else None,
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "average_rank": metrics.average_rank if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
                "response_count": metrics.response_count if metrics else 0,
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


VISIBILITY_CHART_LABEL_LIMIT = 5
TOPIC_VISIBILITY_RANK_LIMIT = 5


def _top_brand_labels_for_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    limit: int = TOPIC_VISIBILITY_RANK_LIMIT,
) -> list[str | None]:
    """按可见度份额取前 N 个品牌 label，不足补 null。"""
    if not rows:
        return [None] * limit
    rank = _rank_from_rows(rows, subject=subject)
    share = rank["visibility_share"]
    top = sorted(share.keys(), key=lambda k: share.get(k, 0), reverse=True)[:limit]
    padded: list[str | None] = list(top)
    while len(padded) < limit:
        padded.append(None)
    return padded[:limit]


def build_topic_visibility_ranks(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """各主题下按可见度排序的品牌 Top5（用于主题可见度排名表）。"""
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
    )
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
    }
    by_topic: dict[UUID, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        p = prompts.get(r.prompt_id)
        if p:
            by_topic[p.topic_id].append(r)

    out: list[dict[str, Any]] = []
    for tid in sorted(topics.keys(), key=lambda k: topics[k].name):
        t = topics[tid]
        out.append(
            {
                "topic_id": str(tid),
                "topic_name": t.name,
                "ranks": _top_brand_labels_for_rows(by_topic.get(tid, []), subject=subject),
            }
        )
    return out


def _previous_date_range(dt_from: datetime, dt_to: datetime) -> tuple[datetime, datetime]:
    span = dt_to - dt_from
    prev_to = dt_from - timedelta(milliseconds=1)
    prev_from = prev_to - span
    return prev_from, prev_to


def _top_visibility_labels(visibility_share: dict[str, float], own: str, limit: int = VISIBILITY_CHART_LABEL_LIMIT) -> list[str]:
    ranked = sorted(visibility_share.keys(), key=lambda k: visibility_share.get(k, 0), reverse=True)
    top = ranked[:limit]
    if own and own not in top and own in visibility_share:
        top = ranked[: limit - 1] + [own]
    return top


def _slim_daily_series(
    series: list[dict[str, Any]],
    label_keys: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "date": pt["date"],
            "values": {k: pt["values"].get(k, 0) for k in label_keys},
        }
        for pt in series
    ]


def _align_previous_daily_to_current(
    current_series: list[dict[str, Any]],
    previous_series: list[dict[str, Any]],
    labels: list[str],
    *,
    current_start: date,
    previous_start: date,
) -> list[dict[str, Any]]:
    prev_by_offset: dict[int, dict[str, Any]] = {}
    for pt in previous_series:
        day = date.fromisoformat(pt["date"])
        prev_by_offset[(day - previous_start).days] = pt

    aligned: list[dict[str, Any]] = []
    for pt in current_series:
        day = date.fromisoformat(pt["date"])
        offset = (day - current_start).days
        prev_pt = prev_by_offset.get(offset)
        values = {lab: (prev_pt["values"].get(lab, 0) if prev_pt else 0) for lab in labels}
        aligned.append(
            {
                "date": pt["date"],
                "values": values,
            }
        )
    return aligned


def build_visibility_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    """Rank + daily 序列，并附带上一周期 rank 与自有品牌对齐 daily 序列。"""
    prev_from, prev_to = _previous_date_range(dt_from, dt_to)
    all_rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=prev_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    current_rows = [r for r in all_rows if dt_from <= r.created_at <= dt_to]
    prev_rows = [r for r in all_rows if prev_from <= r.created_at <= prev_to]

    rank = _rank_from_rows(current_rows, subject=subject)
    prev_rank = _rank_from_rows(prev_rows, subject=subject)
    labels = _top_visibility_labels(rank["visibility_share"], rank["own_label"])
    share_voice_labels = _top_visibility_labels(rank["share_voice"], rank["own_label"])
    series = _slim_daily_series(
        _daily_share_series_from_rows(current_rows, subject=subject, metric="visibility"),
        labels,
    )
    mention_series = _slim_daily_series(
        _daily_share_series_from_rows(current_rows, subject=subject, metric="mention"),
        labels,
    )
    average_rank_series = _daily_average_rank_series_from_rows(current_rows, subject=subject)
    own = rank["own_label"]

    return {
        "own_label": own,
        "labels": labels,
        "share_voice_labels": share_voice_labels,
        "rank": rank,
        "series": series,
        "mention_series": mention_series,
        "average_rank_series": average_rank_series,
        "previous_rank": prev_rank,
        "previous_series": _align_previous_daily_to_current(
            series,
            _daily_share_series_from_rows(prev_rows, subject=subject, metric="visibility"),
            [own],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "previous_mention_series": _align_previous_daily_to_current(
            mention_series,
            _daily_share_series_from_rows(prev_rows, subject=subject, metric="mention"),
            [own],
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "previous_average_rank_series": _align_previous_single_series(
            average_rank_series,
            _daily_average_rank_series_from_rows(prev_rows, subject=subject),
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "topic_visibility_ranks": build_topic_visibility_ranks(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platforms=platforms,
        ),
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
                "visibility_rate": metrics.visibility_rate if metrics else None,
                "mention_intensity": metrics.mention_intensity if metrics else None,
                "citation_rate": metrics.citation_rate if metrics else None,
                "sentiment_score": metrics.sentiment_score if metrics else None,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


PLATFORM_MATRIX_METRICS = ("visibility", "share_voice", "citation", "average_rank", "sentiment")

_METRIC_FIELDS = {
    "visibility": "visibility_rate",
    "share_voice": "share_voice",
    "citation": "citation_rate",
    "average_rank": "average_rank",
    "sentiment": "sentiment_score",
}


def _citation_share_by_label(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    labels: list[str],
) -> dict[str, float | None]:
    own = _own_label(subject)
    total = len(rows)
    if total == 0:
        return {lab: None for lab in labels}
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
    return {k: round(v / total, 4) for k, v in cite_counts.items()}


def _platform_metrics_from_rows(
    rows_by_platform: dict[str, list[LLMResponse]],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for platform, prows in rows_by_platform.items():
        metrics = compute_subject_metrics(prows, subject=subject)
        out.append(
            {
                "platform": platform,
                "visibility_rate": metrics.visibility_rate,
                "share_voice": metrics.share_voice,
                "citation_rate": metrics.citation_rate,
                "average_rank": metrics.average_rank,
                "sentiment_score": metrics.sentiment_score,
            }
        )
    return sorted(out, key=lambda x: -(x["visibility_rate"] or 0))


def _daily_platform_metric_series(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    field: str,
) -> list[dict[str, Any]]:
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)
    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        metrics = compute_subject_metrics(by_date[day], subject=subject)
        series.append({"date": day.isoformat(), "value": getattr(metrics, field)})
    return series


def build_platform_matrix_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
) -> dict[str, Any]:
    """平台矩阵：竞争对手/主题 × 平台 × 指标，含平台排名与分平台趋势。"""
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
    prompts = {
        p.id: p for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }
    topics = {
        t.id: t for t in db.execute(select(Topic).where(Topic.subject_id == subject.id)).scalars().all()
    }

    by_platform_current: dict[str, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_platform_current[r.platform].append(r)

    platforms = sorted(by_platform_current.keys())
    competitor_rows = [{"id": lab, "label": lab, "is_own": lab == own} for lab in labels]
    topic_rows = [{"id": str(tid), "label": topics[tid].name} for tid in sorted(topics.keys(), key=lambda k: topics[k].name)]

    competitor_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {lab: {} for lab in labels} for metric in PLATFORM_MATRIX_METRICS
    }
    topic_values: dict[str, dict[str, dict[str, float | None]]] = {
        metric: {str(tid): {} for tid in topics} for metric in PLATFORM_MATRIX_METRICS
    }

    for platform, prows in by_platform_current.items():
        rank = _rank_from_rows(prows, subject=subject)
        citation = _citation_share_by_label(prows, subject=subject, labels=labels)
        own_metrics = compute_subject_metrics(prows, subject=subject)

        for lab in labels:
            competitor_values["visibility"][lab][platform] = rank["visibility_share"].get(lab)
            competitor_values["share_voice"][lab][platform] = rank["share_voice"].get(lab)
            competitor_values["citation"][lab][platform] = citation.get(lab)
            competitor_values["average_rank"][lab][platform] = rank["average_rank"].get(lab)
            competitor_values["sentiment"][lab][platform] = (
                own_metrics.sentiment_score if lab == own else None
            )

        by_topic: dict[UUID, list[LLMResponse]] = defaultdict(list)
        for r in prows:
            prompt = prompts.get(r.prompt_id)
            if prompt:
                by_topic[prompt.topic_id].append(r)
        for tid, trows in by_topic.items():
            metrics = compute_subject_metrics(trows, subject=subject)
            tid_key = str(tid)
            topic_values["visibility"][tid_key][platform] = metrics.visibility_rate
            topic_values["share_voice"][tid_key][platform] = metrics.share_voice
            topic_values["citation"][tid_key][platform] = metrics.citation_rate
            topic_values["average_rank"][tid_key][platform] = metrics.average_rank
            topic_values["sentiment"][tid_key][platform] = metrics.sentiment_score

    platform_series: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for platform in platforms:
        prows = by_platform_current[platform]
        platform_series[platform] = {
            metric: _daily_platform_metric_series(prows, subject=subject, field=_METRIC_FIELDS[metric])
            for metric in PLATFORM_MATRIX_METRICS
        }

    return {
        "own_label": own,
        "platforms": platforms,
        "competitor_rows": competitor_rows,
        "topic_rows": topic_rows,
        "competitor_values": competitor_values,
        "topic_values": topic_values,
        "platform_performance": _platform_metrics_from_rows(by_platform_current, subject=subject),
        "platform_series": platform_series,
    }


def _citation_share_from_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
) -> tuple[dict[str, int], dict[str, float], str]:
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
    return cite_counts, citation_share, own


def _daily_citation_share_series(
    rows: list[LLMResponse],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    labels = _rank_labels(subject)
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        _, citation_share, _ = _citation_share_from_rows(by_date[day], subject=subject)
        series.append({"date": day.isoformat(), "values": {lab: citation_share.get(lab, 0) for lab in labels}})
    return series


def _aggregate_citation_domains(rows: list[LLMResponse]) -> list[dict[str, Any]]:
    host_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for h in (r.parsed or {}).get("url_hosts") or []:
            if h:
                host_counts[str(h)] += 1
    total = len(rows)
    return sorted(
        [
            {
                "host": host,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
                "monthly_visits": None,
                "domain_type": None,
            }
            for host, count in host_counts.items()
        ],
        key=lambda row: -row["count"],
    )


def _aggregate_citation_urls(rows: list[LLMResponse]) -> list[dict[str, Any]]:
    url_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for url in (r.parsed or {}).get("urls") or []:
            if url:
                url_counts[str(url)] += 1
    total = len(rows)
    return sorted(
        [
            {
                "url": url,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
            }
            for url, count in url_counts.items()
        ],
        key=lambda row: -row["count"],
    )


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
    prev_from, prev_to = _previous_date_range(dt_from, dt_to)
    all_rows = _responses_in_window(
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

    cite_counts, citation_share, own = _citation_share_from_rows(current_rows, subject=subject)
    prev_counts, prev_share, _ = _citation_share_from_rows(prev_rows, subject=subject)
    labels = _top_visibility_labels(citation_share, own)

    series = _slim_daily_series(_daily_citation_share_series(current_rows, subject=subject), labels)
    prev_raw = _daily_citation_share_series(prev_rows, subject=subject)

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
        "previous_series": _align_previous_daily_to_current(
            series,
            prev_raw,
            labels,
            current_start=dt_from.date(),
            previous_start=prev_from.date(),
        ),
        "domains": _aggregate_citation_domains(current_rows),
        "urls": _aggregate_citation_urls(current_rows),
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
    rows = _responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platforms=platforms,
        topic_id=topic_id,
    )
    cite_counts, citation_share, own = _citation_share_from_rows(rows, subject=subject)
    return {
        "own_label": own,
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
            }
        )

    return {"own_label": _own_label(subject), "series": series}


def _reply_text(raw_text: str) -> str:
    return (raw_text or "").replace("\n", " ").strip()


def _daily_sentiment_distribution(rows: list[LLMResponse]) -> list[dict[str, Any]]:
    """按日统计自有品牌提及回复的情感占比（正面 / 中立 / 负面）。"""
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        if _mentions_own(r.parsed or {}):
            by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for r in by_date[day]:
            label = (r.parsed or {}).get("sentiment_own") or "neutral"
            if label not in counts:
                label = "neutral"
            counts[label] += 1
        total = sum(counts.values()) or 1
        series.append(
            {
                "date": day.isoformat(),
                "positive": round(counts["positive"] / total, 4),
                "neutral": round(counts["neutral"] / total, 4),
                "negative": round(counts["negative"] / total, 4),
            }
        )
    return series


def build_sentiment_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platforms: list[str] | None = None,
    topic_id: UUID | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """情感倾向页：分布趋势、平台排名、回复明细。"""
    prev_from, prev_to = _previous_date_range(dt_from, dt_to)
    all_rows = _responses_in_window(
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

    metrics = compute_subject_metrics(current_rows, subject=subject)
    by_platform_current: dict[str, list[LLMResponse]] = defaultdict(list)
    for r in current_rows:
        by_platform_current[r.platform].append(r)
    by_platform_prev: dict[str, list[LLMResponse]] = defaultdict(list)
    for r in prev_rows:
        by_platform_prev[r.platform].append(r)

    prompts = {
        p.id: p
        for p in db.execute(select(Prompt).where(Prompt.subject_id == subject.id)).scalars().all()
    }

    responses: list[dict[str, Any]] = []
    for r in sorted(current_rows, key=lambda row: row.created_at, reverse=True):
        parsed = r.parsed or {}
        if not _mentions_own(parsed):
            continue
        prompt = prompts.get(r.prompt_id)
        responses.append(
            {
                "response_id": str(r.id),
                "platform": r.platform,
                "prompt_id": str(r.prompt_id),
                "prompt_text": prompt.text if prompt else "",
                "sentiment": parsed.get("sentiment_own") or "neutral",
                "sentiment_score": safe_float(parsed, "sentiment_score_own"),
                "reply_preview": _reply_text(r.raw_text),
                "created_at": r.created_at.isoformat(),
            }
        )

    platform_performance = _platform_metrics_from_rows(by_platform_current, subject=subject)
    platform_performance.sort(key=lambda row: -(row["sentiment_score"] or -1))

    return {
        "own_label": _own_label(subject),
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
        "distribution_series": _daily_sentiment_distribution(current_rows),
        "platform_performance": platform_performance,
        "previous_platform_performance": _platform_metrics_from_rows(by_platform_prev, subject=subject),
        "responses": responses,
    }
