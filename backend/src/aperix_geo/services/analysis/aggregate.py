"""Unified KPI aggregation from entity signal rows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from uuid import UUID

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.analysis.entity import AnalysisEntity, list_analysis_entities
from aperix_geo.services.analysis.metrics import MetricsBundle
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.utils.sentiment import has_mention_rank, has_sentiment_score

GroupBy = Literal["none", "entity", "prompt", "topic", "platform", "date"]

SORTABLE_METRICS = (
    "visibility_rate",
    "mention_rate",
    "share_voice",
    "average_rank",
    "citation_rate",
    "sentiment_score",
    "response_count",
)


@dataclass(frozen=True)
class AggregatedMetrics:
    totals: MetricsBundle
    rows: list[dict[str, Any]]


def _response_count(signals: Iterable[LLMResponseSignalRow]) -> int:
    return len({row.response_id for row in signals})


def metrics_from_signals(
    entity_signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    all_signals_for_voice: list[LLMResponseSignalRow] | None = None,
) -> MetricsBundle:
    """Compute KPI bundle for one entity's signal rows (one row per response)."""
    n = _response_count(entity_signals)
    if n == 0:
        return MetricsBundle(
            response_count=0,
            visibility_rate=None,
            mention_rate=None,
            share_voice=None,
            average_rank=None,
            citation_rate=None,
            sentiment_score=None,
            sentiment_count={"positive": 0, "neutral": 0, "negative": 0},
            citation_coverage=None,
        )

    mention_rows = sum(1 for row in entity_signals if row.mentioned)
    mention_count_total = sum(row.mention_count for row in entity_signals)
    ranks = [float(row.mention_rank) for row in entity_signals if has_mention_rank(row.mention_rank)]
    own_domain_link_rows = sum(1 for row in entity_signals if row.has_domain_link)
    cited_on_source_rows = sum(1 for row in entity_signals if row.cited_on_source)
    sentiment_scores = [
        row.sentiment_score for row in entity_signals if row.mentioned and has_sentiment_score(row.sentiment_score)
    ]
    sentiment_count: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    for row in entity_signals:
        if not row.mentioned:
            continue
        label = row.sentiment_label or "neutral"
        if label not in sentiment_count:
            label = "neutral"
        sentiment_count[label] += 1
    cited_all = sum(1 for row in entity_signals if row.cited_on_source)

    voice_pool = all_signals_for_voice if all_signals_for_voice is not None else entity_signals
    total_voice = sum(row.mention_count for row in voice_pool)

    avg_sentiment = None
    if sentiment_scores:
        avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 1)

    return MetricsBundle(
        response_count=n,
        visibility_rate=round(mention_rows / n, 4),
        mention_rate=round(mention_count_total / n, 4),
        share_voice=round(mention_count_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        citation_rate=round(cited_on_source_rows / own_domain_link_rows, 4) if own_domain_link_rows > 0 else None,
        sentiment_score=avg_sentiment,
        sentiment_count=sentiment_count,
        citation_coverage=round(cited_all / n, 4)
        if subject.type == SubjectType.domain or subject.website_url
        else None,
    )


def _metrics_to_dict(metrics: MetricsBundle) -> dict[str, Any]:
    return {
        "response_count": metrics.response_count,
        "visibility_rate": metrics.visibility_rate,
        "mention_rate": metrics.mention_rate,
        "share_voice": metrics.share_voice,
        "average_rank": metrics.average_rank,
        "citation_rate": metrics.citation_rate,
        "sentiment_score": metrics.sentiment_score,
        "sentiment_count": metrics.sentiment_count,
        "citation_coverage": metrics.citation_coverage,
    }


def aggregate_metrics(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    group_by: GroupBy = "none",
    entity_id: str | None = None,
    label_lookup: Callable[[str], str] | None = None,
) -> AggregatedMetrics:
    """Aggregate signals; filter to entity_id when group_by is none."""
    all_signals = signals
    if group_by == "none":
        filtered = [row for row in signals if row.entity_id == entity_id] if entity_id else signals
        totals = metrics_from_signals(filtered, subject=subject, all_signals_for_voice=all_signals)
        return AggregatedMetrics(totals=totals, rows=[])

    if group_by == "entity":
        rows: list[dict[str, Any]] = []
        for entity in list_analysis_entities(subject):
            subset = [row for row in signals if row.entity_id == entity.id]
            metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
            rows.append(
                {
                    "id": entity.id,
                    "label": entity.label,
                    "display_name": entity.display_name,
                    "kind": entity.kind,
                    "is_own": entity.kind == "own",
                    "metrics": _metrics_to_dict(metrics),
                }
            )
        return AggregatedMetrics(totals=MetricsBundle(0, None, None, None, None, None, None, {}, None), rows=rows)

    key_fn: Callable[[LLMResponseSignalRow], object]
    if group_by == "prompt":
        key_fn = lambda row: row.prompt_id
    elif group_by == "platform":
        key_fn = lambda row: row.platform
    elif group_by == "date":
        key_fn = lambda row: row.created_at.date()
    else:
        raise ValueError(f"Unsupported group_by: {group_by}")

    if entity_id:
        signals = [row for row in signals if row.entity_id == entity_id]

    grouped: dict[object, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        grouped[key_fn(row)].append(row)

    out_rows: list[dict[str, Any]] = []
    for key, subset in grouped.items():
        metrics = metrics_from_signals(subset, subject=subject, all_signals_for_voice=all_signals)
        row_id = str(key)
        label = label_lookup(row_id) if label_lookup else row_id
        out_rows.append({"id": row_id, "label": label, "metrics": _metrics_to_dict(metrics)})

    totals = metrics_from_signals(signals, subject=subject, all_signals_for_voice=all_signals)
    return AggregatedMetrics(totals=totals, rows=out_rows)


def sort_metric_rows(
    rows: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str = "desc",
) -> list[dict[str, Any]]:
    if not sort_by or sort_by not in SORTABLE_METRICS:
        return rows
    reverse = order != "asc"

    def key(row: dict[str, Any]) -> float:
        value = row.get("metrics", {}).get(sort_by)
        if value is None:
            return float("-inf") if reverse else float("inf")
        return float(value)

    if sort_by == "average_rank":
        reverse = order == "asc"

        def rank_key(row: dict[str, Any]) -> float:
            value = row.get("metrics", {}).get("average_rank")
            if value is None:
                return float("inf") if reverse else float("-inf")
            return float(value)

        return sorted(rows, key=rank_key, reverse=reverse)

    return sorted(rows, key=key, reverse=reverse)


def rank_dict_from_entity_rows(rows: list[dict[str, Any]], *, own_label: str) -> dict[str, Any]:
    """Build rank API payload from group_by=entity rows."""
    visibility_counts: dict[str, int] = {}
    voice_counts: dict[str, int] = {}
    visibility_share: dict[str, float] = {}
    mention_rate: dict[str, float] = {}
    share_voice: dict[str, float] = {}
    average_rank: dict[str, float | None] = {}
    citation_share: dict[str, float] = {}
    sentiment_score: dict[str, float | None] = {}

    total = 0
    for row in rows:
        label = row["label"]
        metrics = row["metrics"]
        n = int(metrics.get("response_count") or 0)
        total = max(total, n)
        vis = metrics.get("visibility_rate")
        if vis is not None:
            visibility_counts[label] = round(vis * n)
        mention_rate[label] = metrics.get("mention_rate")
        mr = metrics.get("mention_rate")
        if mr is not None and n:
            voice_counts[label] = round(mr * n)
        visibility_share[label] = vis if vis is not None else 0
        share_voice[label] = metrics.get("share_voice")
        average_rank[label] = metrics.get("average_rank")
        cr = metrics.get("citation_rate")
        citation_share[label] = cr if cr is not None else 0
        sentiment_score[label] = metrics.get("sentiment_score")

    return {
        "own_label": own_label,
        "mention_counts": voice_counts,
        "visibility_counts": visibility_counts,
        "visibility_share": visibility_share,
        "mention_rate": mention_rate,
        "share_voice": share_voice,
        "average_rank": average_rank,
        "citation_share": citation_share,
        "sentiment_score": sentiment_score,
    }


def group_signals_by_topic(
    signals: list[LLMResponseSignalRow],
    *,
    prompt_to_topic: dict[UUID, UUID],
) -> dict[UUID, list[LLMResponseSignalRow]]:
    grouped: dict[UUID, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        topic_id = prompt_to_topic.get(row.prompt_id)
        if topic_id is not None:
            grouped[topic_id].append(row)
    return grouped


def citation_share_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
) -> tuple[dict[str, int], dict[str, float], str]:
    from aperix_geo.services.analysis.entity import list_analysis_entities, own_entity

    own = own_entity(subject)
    counts: dict[str, int] = {}
    share: dict[str, float] = {}
    for entity in list_analysis_entities(subject):
        subset = [row for row in signals if row.entity_id == entity.id]
        n = _response_count(subset)
        cited = sum(1 for row in subset if row.cited_on_source)
        counts[entity.label] = cited
        share[entity.label] = round(cited / n, 4) if n else 0.0
    return counts, share, own.label


def daily_share_series_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    metric: str,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis.entity import list_analysis_entities

    entities = list_analysis_entities(subject)
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        values: dict[str, float] = {}
        for entity in entities:
            subset = [row for row in day_rows if row.entity_id == entity.id]
            n = _response_count(subset)
            if metric == "share_voice":
                total_voice = sum(row.mention_count for row in day_rows)
                voice = sum(row.mention_count for row in subset)
                values[entity.label] = round(voice / total_voice, 4) if total_voice else 0.0
            elif metric == "mention":
                mention_total = sum(row.mention_count for row in subset)
                values[entity.label] = round(mention_total / n, 4) if n else 0.0
            else:
                mentioned = sum(1 for row in subset if row.mentioned)
                values[entity.label] = round(mentioned / n, 4) if n else 0.0
        series.append({"date": day.isoformat(), "values": values})
    return series


def daily_average_rank_series_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        if row.entity_id == entity_id:
            by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        ranks = [float(row.mention_rank) for row in by_date[day] if has_mention_rank(row.mention_rank)]
        series.append(
            {
                "date": day.isoformat(),
                "value": round(sum(ranks) / len(ranks), 2) if ranks else None,
            }
        )
    return series


def daily_citation_share_series_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    from aperix_geo.services.analysis.entity import list_analysis_entities

    entities = list_analysis_entities(subject)
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        day_rows = by_date[day]
        values: dict[str, float] = {}
        for entity in entities:
            subset = [row for row in day_rows if row.entity_id == entity.id]
            n = _response_count(subset)
            cited = sum(1 for row in subset if row.cited_on_source)
            values[entity.label] = round(cited / n, 4) if n else 0.0
        series.append({"date": day.isoformat(), "values": values})
    return series


def daily_sentiment_distribution_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        if row.entity_id == entity_id and row.mentioned:
            by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for row in by_date[day]:
            label = row.sentiment_label or "neutral"
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


def daily_platform_metric_series_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    entity_id: str,
    field: str,
) -> list[dict[str, Any]]:
    entity_by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        if row.entity_id == entity_id:
            entity_by_date[row.created_at.date()].append(row)

    series: list[dict[str, Any]] = []
    for day in sorted(entity_by_date.keys()):
        day_entity = entity_by_date[day]
        day_voice = [row for row in signals if row.created_at.date() == day]
        metrics = metrics_from_signals(day_entity, subject=subject, all_signals_for_voice=day_voice)
        series.append({"date": day.isoformat(), "value": getattr(metrics, field)})
    return series


def other_mentioned_entity_labels(
    response_ids: set[UUID],
    *,
    all_signals: list[LLMResponseSignalRow],
    exclude_entity_id: str,
    subject: Subject,
) -> list[str]:
    from aperix_geo.services.analysis.entity import list_analysis_entities

    label_by_id = {entity.id: entity.label for entity in list_analysis_entities(subject)}
    seen: set[str] = set()
    labels: list[str] = []
    for row in all_signals:
        if row.response_id not in response_ids:
            continue
        if row.entity_id == exclude_entity_id or not row.mentioned:
            continue
        label = label_by_id.get(row.entity_id)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def top_entity_labels_by_visibility(
    signals: list[LLMResponseSignalRow],
    *,
    subject: Subject,
    limit: int = 5,
) -> list[str | None]:
    aggregated = aggregate_metrics(signals, subject=subject, group_by="entity")
    ranked = sorted(
        aggregated.rows,
        key=lambda row: -(row["metrics"].get("visibility_rate") or 0),
    )
    top = [row["label"] for row in ranked[:limit]]
    while len(top) < limit:
        top.append(None)  # type: ignore[arg-type]
    return top[:limit]
