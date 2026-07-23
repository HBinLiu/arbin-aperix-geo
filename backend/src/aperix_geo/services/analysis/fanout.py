"""Subject-level query fan-out analysis (search queries from engine tool traces)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject
from aperix_geo.services.analysis._page import normalize_pagination
from aperix_geo.services.analysis._query import responses_in_window
from aperix_geo.services.analysis._series import align_previous_daily_to_current, previous_date_range
from aperix_geo.services.analysis.catalog import load_topic_prompt_catalog
from aperix_geo.services.sampling.fanout import normalize_fanout_query_key, search_queries_from_parsed
from aperix_geo.services.sampling.llm import list_sampling_platforms

FanoutPromptSortField = Literal["quantity"]
TOP_QUERIES_PREVIEW = 5


def _platform_labels() -> dict[str, str]:
    return {item["platform"]: item["label"] for item in list_sampling_platforms()}


def _day_of(created_at: datetime) -> date:
    return created_at.date() if isinstance(created_at, datetime) else date.fromisoformat(str(created_at)[:10])


def _iter_days(dt_from: datetime, dt_to: datetime) -> list[date]:
    start = dt_from.date()
    end = dt_to.date()
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _collect_query_events(
    response_rows: list[Any],
) -> list[tuple[date, str, UUID, str]]:
    """(day, platform, prompt_id, query) occurrence rows."""
    events: list[tuple[date, str, UUID, str]] = []
    for row in response_rows:
        prompt_id = getattr(row, "prompt_id", None)
        if prompt_id is None:
            continue
        platform = str(getattr(row, "platform", "") or "").strip()
        created_at = getattr(row, "created_at", None)
        if created_at is None:
            continue
        day = _day_of(created_at)
        parsed = row.parsed if isinstance(getattr(row, "parsed", None), dict) else {}
        for query in search_queries_from_parsed(parsed):
            events.append((day, platform, prompt_id, query))
    return events


def _platform_totals(events: list[tuple[date, str, UUID, str]]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for _day, platform, _prompt_id, _query in events:
        if platform:
            totals[platform] += 1
    return dict(totals)


def _daily_platform_series(
    events: list[tuple[date, str, UUID, str]],
    *,
    dt_from: datetime,
    dt_to: datetime,
    platform_ids: list[str],
) -> list[dict[str, Any]]:
    by_day: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for day, platform, _prompt_id, _query in events:
        if platform:
            by_day[day][platform] += 1
    series: list[dict[str, Any]] = []
    for day in _iter_days(dt_from, dt_to):
        values = {pid: float(by_day.get(day, {}).get(pid, 0)) for pid in platform_ids}
        series.append({"date": day.isoformat(), "values": values})
    return series


def _rank_table(
    current: dict[str, int],
    previous: dict[str, int],
    *,
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for platform_id in sorted(current.keys(), key=lambda key: current[key], reverse=True):
        rows.append(
            {
                "id": platform_id,
                "label": labels.get(platform_id, platform_id),
                "domain": "",
                "cur_value": float(current[platform_id]),
                "pre_value": float(previous.get(platform_id, 0)),
            }
        )
    return rows


def _query_frequency_items(
    events: list[tuple[date, str, UUID, str]],
) -> list[dict[str, Any]]:
    """Dedupe by normalize key; sort by frequency desc."""
    freq: dict[str, dict[str, Any]] = {}
    for _day, platform, _prompt_id, query in events:
        key = normalize_fanout_query_key(query)
        if not key:
            continue
        bucket = freq.get(key)
        if bucket is None:
            bucket = {"query": query, "frequency": 0, "platforms": set(), "platform_counts": {}}
            freq[key] = bucket
        bucket["frequency"] = int(bucket["frequency"]) + 1
        if platform:
            cast_platforms = bucket["platforms"]
            assert isinstance(cast_platforms, set)
            cast_platforms.add(platform)
            counts = bucket["platform_counts"]
            assert isinstance(counts, dict)
            counts[platform] = int(counts.get(platform) or 0) + 1
    items = sorted(
        freq.values(),
        key=lambda item: (-int(item["frequency"]), str(item["query"])),
    )
    total_frequency = sum(int(item["frequency"]) for item in items)
    return [
        {
            "query": str(item["query"]),
            "frequency": int(item["frequency"]),
            "platforms": sorted(item["platforms"]),
            "platform_counts": {
                str(pid): int(cnt)
                for pid, cnt in dict(item["platform_counts"]).items()
                if int(cnt or 0) > 0
            },
            "contribution_rate": (
                round(int(item["frequency"]) / total_frequency, 4) if total_frequency else 0.0
            ),
        }
        for item in items
    ]


def build_fanout_analysis(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    prompt_id: UUID | None = None,
) -> dict[str, Any]:
    """Overview: total query occurrences, daily multi-platform series, platform rank."""
    prev_from, prev_to = previous_date_range(dt_from, dt_to)
    labels = _platform_labels()

    current_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    previous_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=prev_from,
        dt_to=prev_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )

    current_events = _collect_query_events(current_rows)
    previous_events = _collect_query_events(previous_rows)
    current_totals = _platform_totals(current_events)
    previous_totals = _platform_totals(previous_events)

    platform_ids = sorted(
        set(current_totals) | set(previous_totals),
        key=lambda pid: (-current_totals.get(pid, 0), pid),
    )
    if platform:
        allowed = {str(p).strip() for p in platform if str(p).strip()}
        platform_ids = [pid for pid in platform_ids if pid in allowed]

    series = _daily_platform_series(
        current_events,
        dt_from=dt_from,
        dt_to=dt_to,
        platform_ids=platform_ids,
    )
    previous_series_raw = _daily_platform_series(
        previous_events,
        dt_from=prev_from,
        dt_to=prev_to,
        platform_ids=platform_ids,
    )
    previous_series = align_previous_daily_to_current(
        series,
        previous_series_raw,
        platform_ids,
        current_start=dt_from.date(),
        previous_start=prev_from.date(),
    )

    return {
        "fanout_count": len(current_events),
        "fanout_previous": len(previous_events),
        "labels": platform_ids,
        "series": series,
        "previous_series": previous_series,
        "rank_table": _rank_table(current_totals, previous_totals, labels=labels),
    }


def _is_root_prompt(prompt: Prompt) -> bool:
    kind = str(getattr(prompt, "kind", "") or "root").strip().lower()
    return kind in ("", "root")


def _prompt_aggregates(
    events: list[tuple[date, str, UUID, str]],
    *,
    dt_from: datetime,
    dt_to: datetime,
) -> dict[UUID, dict[str, Any]]:
    aggregates: dict[UUID, dict[str, Any]] = {}
    events_by_prompt: dict[UUID, list[tuple[date, str, UUID, str]]] = defaultdict(list)

    for event in events:
        day, platform, prompt_id, _query = event
        events_by_prompt[prompt_id].append(event)
        bucket = aggregates.get(prompt_id)
        if bucket is None:
            bucket = {
                "quantity": 0,
                "platform_counts": defaultdict(int),
                "daily": defaultdict(int),
            }
            aggregates[prompt_id] = bucket
        bucket["quantity"] = int(bucket["quantity"]) + 1
        if platform:
            cast_counts = bucket["platform_counts"]
            assert isinstance(cast_counts, defaultdict)
            cast_counts[platform] += 1
        cast_daily = bucket["daily"]
        assert isinstance(cast_daily, defaultdict)
        cast_daily[day] += 1

    days = _iter_days(dt_from, dt_to)
    for prompt_id, bucket in aggregates.items():
        daily = bucket.pop("daily")
        bucket["platform_counts"] = dict(bucket["platform_counts"])
        bucket["series"] = [
            {"date": day.isoformat(), "value": float(daily.get(day, 0))} for day in days
        ]
        query_items = _query_frequency_items(events_by_prompt[prompt_id])
        bucket["unique_count"] = len(query_items)
        bucket["top_queries"] = query_items[:TOP_QUERIES_PREVIEW]
    return aggregates


def build_fanout_prompts_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    sort_by: FanoutPromptSortField | None = "quantity",
    order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Paginated root prompts that have fan-out; each row includes top 5 sub-queries."""
    page, page_size = normalize_pagination(page, page_size)
    offset = (page - 1) * page_size
    topics, prompts, _prompt_to_topic = load_topic_prompt_catalog(db, subject.id)

    response_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    events = _collect_query_events(response_rows)
    aggregates = _prompt_aggregates(events, dt_from=dt_from, dt_to=dt_to)

    needle = (search or "").strip().lower()
    items: list[dict[str, Any]] = []
    for prompt_id, stats in aggregates.items():
        prompt: Prompt | None = prompts.get(prompt_id)
        if prompt is None:
            continue
        if bool(getattr(prompt, "deleted", False)):
            continue
        if not _is_root_prompt(prompt):
            continue
        text = str(getattr(prompt, "text", "") or "")
        if needle and needle not in text.lower():
            continue
        topic = topics.get(prompt.topic_id) if prompt.topic_id else None
        items.append(
            {
                "prompt_id": str(prompt_id),
                "prompt_text": text,
                "topic_id": str(prompt.topic_id) if prompt.topic_id else "",
                "topic_name": str(getattr(topic, "name", "") or "") if topic else "",
                "quantity": int(stats["quantity"]),
                "unique_count": int(stats["unique_count"]),
                "platform_counts": {
                    str(k): int(v) for k, v in dict(stats["platform_counts"]).items()
                },
                "series": stats["series"],
                "top_queries": stats["top_queries"],
            }
        )

    reverse = order != "asc"
    sort_field = sort_by if sort_by in ("quantity",) else "quantity"
    items.sort(key=lambda row: (int(row[sort_field]), str(row["prompt_text"])), reverse=reverse)

    total = len(items)
    page_items = items[offset : offset + page_size]
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def build_fanout_queries_page(
    db: Session,
    *,
    subject: Subject,
    prompt_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Paginated unique fan-out sub-queries for one root prompt."""
    page, page_size = normalize_pagination(page, page_size)
    offset = (page - 1) * page_size

    response_rows = responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=prompt_id,
    )
    events = _collect_query_events(response_rows)
    items = _query_frequency_items(events)
    total = len(items)
    return {
        "items": items[offset : offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
