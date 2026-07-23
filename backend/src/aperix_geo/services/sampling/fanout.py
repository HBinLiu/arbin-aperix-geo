"""Helpers for query fan-out (search queries from engine tool traces)."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.providers._helpers import dedupe_search_queries

# Platforms whose APIs expose real web-search query text.
FANOUT_QUERY_PLATFORMS: frozenset[str] = frozenset({"doubao", "kimi", "deepseek"})


def platform_exposes_search_queries(platform: str) -> bool:
    return str(platform or "").strip().lower() in FANOUT_QUERY_PLATFORMS


def search_queries_from_parsed(parsed: dict[str, Any] | None) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    raw = [str(q) for q in (parsed.get("search_queries_from_api") or [])]
    return list(dedupe_search_queries(raw))


def build_search_query_events(
    queries: list[str] | tuple[str, ...],
    *,
    platform: str = "",
) -> list[dict[str, Any]]:
    """Ordered events; rank is 1-based within this response."""
    events: list[dict[str, Any]] = []
    for index, query in enumerate(dedupe_search_queries(list(queries))):
        events.append(
            {
                "query": query,
                "platform": str(platform or "").strip(),
                "rank": index + 1,
            }
        )
    return events


def normalize_fanout_query_key(query: str) -> str:
    """Aggregation key: trim + fold full-width spaces; lowercase Latin only."""
    text = (query or "").replace("\u3000", " ").strip()
    if not text:
        return ""
    # Lowercase ASCII letters without touching CJK.
    return "".join(ch.lower() if "A" <= ch <= "Z" else ch for ch in text)


def aggregate_fanout_metrics(
    *,
    response_query_rows: list[tuple[str, list[str]]],
    monitored_query_keys: set[str] | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """L2 metrics from (platform, search_queries) rows for one parent prompt.

    ``response_query_rows``: one entry per LLM response in the window.
    """
    monitored = monitored_query_keys or set()
    freq: dict[str, dict[str, Any]] = {}
    per_response_counts: list[int] = []
    all_unique: set[str] = set()

    for platform, queries in response_query_rows:
        cleaned = [q for q in queries if q.strip()]
        if cleaned:
            per_response_counts.append(len(cleaned))
        for query in cleaned:
            key = normalize_fanout_query_key(query)
            if not key:
                continue
            all_unique.add(key)
            bucket = freq.get(key)
            if bucket is None:
                bucket = {
                    "query": query,
                    "frequency": 0,
                    "platforms": set(),
                }
                freq[key] = bucket
            bucket["frequency"] = int(bucket["frequency"]) + 1
            if platform:
                cast_platforms = bucket["platforms"]
                assert isinstance(cast_platforms, set)
                cast_platforms.add(platform)

    top_queries = sorted(
        freq.values(),
        key=lambda item: (-int(item["frequency"]), str(item["query"])),
    )[: max(1, top_n)]

    unmonitored = [
        {
            "query": str(item["query"]),
            "frequency": int(item["frequency"]),
            "platforms": sorted(item["platforms"]),
        }
        for key, item in sorted(
            freq.items(),
            key=lambda pair: (-int(pair[1]["frequency"]), str(pair[1]["query"])),
        )
        if key not in monitored
    ][: max(1, top_n)]

    avg = (
        round(sum(per_response_counts) / len(per_response_counts), 2)
        if per_response_counts
        else 0.0
    )
    return {
        "fanout_count": len(all_unique),
        "fanout_avg_per_response": avg,
        "top_queries": [
            {
                "query": str(item["query"]),
                "frequency": int(item["frequency"]),
                "platforms": sorted(item["platforms"]),
                "monitored": normalize_fanout_query_key(str(item["query"])) in monitored,
            }
            for item in top_queries
        ],
        "unmonitored_queries": unmonitored,
    }


def monitored_origin_keys(prompts: list[Any]) -> set[str]:
    """Keys already promoted (origin_query or text on fanout prompts)."""
    keys: set[str] = set()
    for prompt in prompts:
        kind = str(getattr(prompt, "kind", "") or "root")
        if kind != "fanout":
            continue
        origin = str(getattr(prompt, "origin_query", "") or "").strip()
        text = str(getattr(prompt, "text", "") or "").strip()
        for value in (origin, text):
            key = normalize_fanout_query_key(value)
            if key:
                keys.add(key)
    return keys
