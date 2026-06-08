"""Brand rank and share-of-voice aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, Subject
from aperix_geo.services.analysis._labels import own_label, rank_labels
from aperix_geo.services.analysis._parsed import avg_sentiment_points, mentions_own, parsed_sentiment_score
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis.citation import citation_share_from_rows
from aperix_geo.utils.coerce import safe_float, safe_int
from aperix_geo.utils.sentiment import sentiment_points


def rank_positions_from_parsed(p: dict[str, Any], labels: list[str]) -> dict[str, int | None]:
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


def accumulate_average_ranks(
    rows: list[LLMResponse],
    *,
    labels: list[str],
    own: str,
) -> dict[str, float | None]:
    """各品牌平均排名：仅统计该品牌在该条回复中有名次的样本。"""
    buckets: dict[str, list[float]] = {lab: [] for lab in labels}
    for r in rows:
        p = r.parsed or {}
        positions = rank_positions_from_parsed(p, labels)
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


def accumulate_rank_counts(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    labels: list[str],
) -> tuple[dict[str, int], dict[str, int], int]:
    own = own_label(subject)
    visibility_counts: dict[str, int] = {lab: 0 for lab in labels}
    voice_counts: dict[str, int] = {lab: 0 for lab in labels}
    total = len(rows)

    for r in rows:
        p = r.parsed or {}
        if mentions_own(p):
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


def accumulate_sentiment_by_label(
    rows: list[LLMResponse],
    *,
    labels: list[str],
    own: str,
) -> dict[str, float | None]:
    """各品牌情感得分（0–100）：仅使用 LLM 裁判写入 parsed 的结果。"""
    buckets: dict[str, list[float]] = {lab: [] for lab in labels}
    for r in rows:
        p = r.parsed or {}
        comp_scores = p.get("sentiment_scores_competitors") or {}
        for lab in labels:
            if lab == own:
                if mentions_own(p):
                    score = parsed_sentiment_score(p)
                    if score is not None:
                        buckets[lab].append(score)
                continue
            mc = p.get("mentions_competitors") or {}
            if not (isinstance(mc, dict) and mc.get(lab)):
                continue
            if isinstance(comp_scores, dict) and lab in comp_scores:
                score = sentiment_points(safe_float({"score": comp_scores[lab]}, "score"))
                if score is not None:
                    buckets[lab].append(score)
    return {lab: avg_sentiment_points(v) for lab, v in buckets.items()}


def rank_from_rows(rows: list[LLMResponse], *, subject: Subject) -> dict[str, Any]:
    own = own_label(subject)
    labels = rank_labels(subject)
    visibility_counts, voice_counts, total = accumulate_rank_counts(rows, subject=subject, labels=labels)

    total_voice = sum(voice_counts.values())
    visibility_share = {k: (round(v / total, 4) if total else 0) for k, v in visibility_counts.items()}
    share_voice_map = {
        k: (round(v / total_voice, 4) if total_voice else 0) for k, v in voice_counts.items()
    }

    mention_rate_map = {
        k: (round(v / total, 4) if total else 0) for k, v in voice_counts.items()
    }
    average_rank = accumulate_average_ranks(rows, labels=labels, own=own)
    _, citation_share, _ = citation_share_from_rows(rows, subject=subject)
    sentiment_score = accumulate_sentiment_by_label(rows, labels=labels, own=own)

    return {
        "own_label": own,
        "mention_counts": voice_counts,
        "visibility_counts": visibility_counts,
        "visibility_share": visibility_share,
        "mention_rate": mention_rate_map,
        "share_voice": share_voice_map,
        "average_rank": average_rank,
        "citation_share": citation_share,
        "sentiment_score": sentiment_score,
    }


def build_rank(
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
    return rank_from_rows(rows, subject=subject)


def daily_share_series_from_rows(
    rows: list[LLMResponse],
    *,
    subject: Subject,
    metric: str,
) -> list[dict[str, Any]]:
    labels = rank_labels(subject)
    by_date: dict[date, list[LLMResponse]] = defaultdict(list)
    for r in rows:
        by_date[r.created_at.date()].append(r)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        visibility_counts, voice_counts, total = accumulate_rank_counts(day_rows, subject=subject, labels=labels)
        counts = visibility_counts if metric == "visibility" else voice_counts
        if metric == "share_voice":
            total_voice = sum(voice_counts.values())
            values = {k: (round(v / total_voice, 4) if total_voice else 0) for k, v in voice_counts.items()}
        else:
            values = {k: (round(v / total, 4) if total else 0) for k, v in counts.items()}
        series.append({"date": day.isoformat(), "values": values})
    return series


def daily_average_rank_series_from_rows(
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
