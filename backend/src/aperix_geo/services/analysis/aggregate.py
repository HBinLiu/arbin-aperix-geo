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
from aperix_geo.services.analysis.signal_index import SignalWindowIndex, index_signals
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow
from aperix_geo.utils.mention import has_mention_rank
from aperix_geo.utils.sentiment import api_sentiment_label, api_sentiment_score, is_scored_sentiment

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
    total_voice: int | None = None,
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
            sentiment_label=None,
            citation_coverage=None,
        )

    mention_rows = sum(1 for row in entity_signals if row.mentioned)
    mention_count_total = sum(row.mention_count for row in entity_signals)
    mention_with_link_rows = sum(
        1 for row in entity_signals if row.mentioned and row.has_domain_link
    )
    ranks = [float(row.mention_rank) for row in entity_signals if has_mention_rank(row.mention_rank)]
    cited_on_source_rows = sum(1 for row in entity_signals if row.cited_on_source)
    sentiment_scores = [
        api_sentiment_score(row.sentiment_score)
        for row in entity_signals
        if is_scored_sentiment(row.sentiment_score)
    ]
    cited_all = sum(1 for row in entity_signals if row.cited_on_source)

    if total_voice is None:
        voice_pool = all_signals_for_voice if all_signals_for_voice is not None else entity_signals
        total_voice = sum(row.mention_count for row in voice_pool)

    if sentiment_scores:
        avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 1)
    else:
        avg_sentiment = 0.0

    return MetricsBundle(
        response_count=n,
        visibility_rate=round(mention_rows / n, 4),
        mention_rate=round(mention_count_total / n, 4),
        share_voice=round(mention_count_total / total_voice, 4) if total_voice > 0 else None,
        average_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        citation_rate=round(mention_with_link_rows / mention_rows, 4) if mention_rows > 0 else None,
        sentiment_score=avg_sentiment,
        sentiment_label=api_sentiment_label(avg_sentiment),
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
        "sentiment_label": metrics.sentiment_label,
        "citation_coverage": metrics.citation_coverage,
    }


def platform_sentiment_rows(
    all_signals: list[LLMResponseSignalRow],
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    """Per-platform average sentiment for one entity (no full KPI aggregation)."""
    by_platform: dict[str, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in all_signals:
        if row.entity_id == entity_id:
            by_platform[row.platform].append(row)

    out: list[dict[str, Any]] = []
    for platform_id, subset in by_platform.items():
        scores = [
            api_sentiment_score(row.sentiment_score)
            for row in subset
            if is_scored_sentiment(row.sentiment_score)
        ]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        out.append(
            {
                "platform_id": platform_id,
                "sentiment_score": avg,
                "sentiment_label": api_sentiment_label(avg),
            }
        )
    return sorted(out, key=lambda row: -(row["sentiment_score"] or -1))


def entity_metrics_rows_from_index(
    index: SignalWindowIndex,
    *,
    subject: Subject,
    entities: list[AnalysisEntity] | None = None,
) -> list[dict[str, Any]]:
    """Per-entity metric rows using pre-grouped signal index (one metrics pass per entity)."""
    entities = entities or list_analysis_entities(subject)
    rows: list[dict[str, Any]] = []
    for entity in entities:
        subset = index.by_entity.get(entity.id, [])
        metrics = metrics_from_signals(subset, subject=subject, total_voice=index.total_voice)
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
    return rows


def daily_visibility_share_from_index(
    index: SignalWindowIndex,
    *,
    entities: list[AnalysisEntity],
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Daily visibility share using pre-indexed by_date_entity (avoids repeated scans)."""
    return daily_share_series_from_index(
        index,
        entities=entities,
        metric="visibility",
        labels=labels,
    )


def daily_share_series_from_index(
    index: SignalWindowIndex,
    *,
    entities: list[AnalysisEntity],
    metric: str,
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Daily multi-brand series from index (visibility / mention / share_voice)."""
    label_set = set(labels) if labels is not None else None
    series: list[dict[str, Any]] = []
    for day in sorted(index.by_date.keys()):
        day_entities = index.by_date_entity[day]
        day_rows = index.by_date[day]
        values: dict[str, float] = {}
        for entity in entities:
            if label_set is not None and entity.label not in label_set:
                continue
            subset = day_entities.get(entity.id, [])
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


def daily_average_rank_series_from_index(
    index: SignalWindowIndex,
    *,
    entity_id: str,
) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for day in sorted(index.by_date.keys()):
        subset = index.by_date_entity[day].get(entity_id, [])
        ranks = [float(row.mention_rank) for row in subset if has_mention_rank(row.mention_rank)]
        series.append(
            {
                "date": day.isoformat(),
                "value": round(sum(ranks) / len(ranks), 2) if ranks else None,
            }
        )
    return series


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
        index = index_signals(signals)
        rows = entity_metrics_rows_from_index(index, subject=subject)
        return AggregatedMetrics(totals=MetricsBundle(0, None, None, None, None, None, None, None, None), rows=rows)

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
    sentiment_label: dict[str, str | None] = {}

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
        sentiment_label[label] = metrics.get("sentiment_label")

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
        "sentiment_label": sentiment_label,
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
        mentioned_rows = sum(1 for row in subset if row.mentioned)
        with_link = sum(1 for row in subset if row.mentioned and row.has_domain_link)
        counts[entity.label] = with_link
        share[entity.label] = round(with_link / mentioned_rows, 4) if mentioned_rows else 0.0
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
            mentioned_rows = sum(1 for row in subset if row.mentioned)
            with_link = sum(1 for row in subset if row.mentioned and row.has_domain_link)
            values[entity.label] = round(with_link / mentioned_rows, 4) if mentioned_rows else 0.0
        series.append({"date": day.isoformat(), "values": values})
    return series


def daily_sentiment_distribution_from_signals(
    signals: list[LLMResponseSignalRow],
    *,
    entity_id: str,
    platform_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Daily positive/neutral/negative shares; optional per-platform avg scores for chart tooltip."""
    by_date: dict[date, list[LLMResponseSignalRow]] = defaultdict(list)
    for row in signals:
        if row.entity_id == entity_id and row.mentioned:
            by_date[row.created_at.date()].append(row)

    platform_filter = set(platform_ids) if platform_ids else None
    series: list[dict[str, Any]] = []
    for day in sorted(by_date.keys()):
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        platform_scores: dict[str, list[float]] = defaultdict(list)
        for row in by_date[day]:
            label = api_sentiment_label(row.sentiment_score)
            counts[label] += 1
            if is_scored_sentiment(row.sentiment_score):
                if platform_filter is None or row.platform in platform_filter:
                    platform_scores[row.platform].append(api_sentiment_score(row.sentiment_score))
        total = sum(counts.values()) or 1
        scores = [
            api_sentiment_score(row.sentiment_score)
            for row in by_date[day]
            if is_scored_sentiment(row.sentiment_score)
        ]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        point: dict[str, Any] = {
            "date": day.isoformat(),
            "positive": round(counts["positive"] / total, 4),
            "neutral": round(counts["neutral"] / total, 4),
            "negative": round(counts["negative"] / total, 4),
            "sentiment_score": avg_score,
            "sentiment_label": api_sentiment_label(avg_score),
        }
        if platform_ids:
            point["platform_scores"] = {
                platform_id: round(sum(scores) / len(scores), 1)
                for platform_id, scores in platform_scores.items()
                if scores
            }
        series.append(point)
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


def mentioned_brands_for_response(
    response_id: UUID,
    *,
    all_signals: list[LLMResponseSignalRow],
    entities: list,
) -> list[dict[str, str | None]]:
    """Closed-set + open-set brands mentioned in one reply, ordered by mention rank."""
    from aperix_geo.db.models import EntityKind
    from aperix_geo.utils.mention import has_mention_rank

    entity_by_id = {entity.id: entity for entity in entities}
    entity_order = {entity.id: index for index, entity in enumerate(entities)}
    rows = [row for row in all_signals if row.response_id == response_id and row.mentioned]
    rows.sort(
        key=lambda row: (
            row.mention_rank if has_mention_rank(row.mention_rank) else 10_000,
            entity_order.get(row.entity_id, 10_000),
            (row.entity_label or row.entity_id).casefold(),
        )
    )

    out: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for row in rows:
        if row.entity_kind == EntityKind.other.value:
            label = (row.entity_label or "").strip()
            if not label:
                continue
            key = label.casefold()
            if key in seen:
                continue
            seen.add(key)
            domain = (row.primary_domain or "").strip() or None
            out.append({"label": label, "domain": domain})
            continue

        entity = entity_by_id.get(row.entity_id)
        if entity is None or entity.label in seen:
            continue
        seen.add(entity.label)
        domain = (entity.domain or "").strip() or None
        out.append({"label": entity.label, "domain": domain})
    return out


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
